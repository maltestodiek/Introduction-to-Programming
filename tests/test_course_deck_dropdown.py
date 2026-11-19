from pathlib import Path
from unittest.mock import Mock

from streamlit.testing.v1 import AppTest

from auth import AuthService
from logic import DEFAULT_AVATAR
from test_deck_ui import Obj


def course_app(monkeypatch,copies=None):
    profile={'username':'student_a','university':'Example University','courses':['Corporate Finance','Investments'],'languages':['English'],'avatar':DEFAULT_AVATAR,'image_mode':'Avatar'}
    battle={'Corporate Finance':[{'id':'battle-cf','name':'Capital structure','course':'Corporate Finance','language':'English','creator_id':'b','profiles':{'username':'student_b'}}],'Investments':[]}
    monkeypatch.setattr('db.ProfileRepository.load',lambda self:profile)
    monkeypatch.setattr('db.DeckRepository.list',lambda self,course:battle[course])
    def publication(self,action,data=None):
        if action=='list':return {'decks':[
            {'id':'study-own','name':'WACC basics','course':'Corporate Finance','language':'English','author':'student_a','count':20,'owned':True},
            {'id':'study-other','name':'Bond pricing','course':'corporate finance ','language':'English','author':'Student B','count':12,'owned':False},
        ]}
        if action=='copy':
            (copies if copies is not None else []).append(data['id']);return {'id':'copy-1'}
        return {}
    monkeypatch.setattr('db.StudyRepository.publication',publication)
    client=Mock();client.auth.get_user.return_value=Obj(user=Obj(id='a'))
    auth=AuthService(client);auth.user=client.auth.get_user.return_value.user
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=20)
    at.session_state['auth']=auth;at.session_state['main_page']='Decks';at.run()
    return at


def test_each_course_card_has_a_deck_dropdown_with_its_own_decks(monkeypatch):
    at=course_app(monkeypatch)
    labels=[item.label for item in at.expander if item.label.startswith('Decks in this course')]
    assert labels==['Decks in this course (3)','Decks in this course (0)']
    finance=next(item for item in at.expander if item.label=='Decks in this course (3)')
    names=[item.value for item in finance.markdown]
    assert any('WACC basics' in name for name in names)
    assert any('Bond pricing' in name for name in names)
    assert any('Capital structure' in name for name in names)
    empty=next(item for item in at.expander if item.label=='Decks in this course (0)')
    assert any('No decks in Investments yet' in item.value for item in empty.caption)
    assert not at.exception


def test_choosing_decks_from_the_dropdown_opens_or_copies_them(monkeypatch):
    copies=[]
    at=course_app(monkeypatch,copies)
    at.button(key='course_menu_0_battle_battle-cf').click().run()
    assert at.session_state['deck_open']=='battle-cf'
    at=course_app(monkeypatch,copies)
    at.button(key='course_menu_0_study_study-own').click().run()
    assert at.session_state['study_deck_open']=={'id':'study-own','shared':False}
    at=course_app(monkeypatch,copies)
    at.button(key='course_menu_0_study_study-other').click().run()
    assert copies==['study-other']
    assert not at.exception
