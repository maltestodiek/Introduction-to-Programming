from pathlib import Path
from unittest.mock import Mock

from streamlit.testing.v1 import AppTest

from auth import AuthService
from logic import DEFAULT_AVATAR
from test_deck_ui import Obj


def course_app(monkeypatch,copies=None):
    profile={'username':'student_a','university':'Example University','courses':['Corporate Finance','Investments'],'languages':['English'],'avatar':DEFAULT_AVATAR,'image_mode':'Avatar'}
    monkeypatch.setattr('db.ProfileRepository.load',lambda self:profile)
    def publication(self,action,data=None):
        if action=='list':return {'decks':[
            {'id':'study-own','name':'WACC basics','course':'Corporate Finance','language':'English','author':'student_a','count':20,'owned':True,'published_at':'2026-11-21T12:00:00+00:00'},
            {'id':'study-other','name':'Bond pricing','course':'corporate finance ','language':'English','author':'Student B','count':12,'owned':False,'in_studio':bool(copies),'published_at':'2026-11-20T12:00:00+00:00'},
        ]}
        if action in ('copy','add_to_studio'):
            (copies if copies is not None else []).append((action,data['id']));return {'id':'copy-1'}
        return {}
    monkeypatch.setattr('db.StudyRepository.publication',publication)
    monkeypatch.setattr('db.StudyRepository.action',lambda self,action,data=None:{
        'decks':[],'shared':[],'invites':[],'open':[],'sessions':[],'friends':[]
    } if action=='list' else {})
    client=Mock();client.auth.get_user.return_value=Obj(user=Obj(id='a'))
    auth=AuthService(client);auth.user=client.auth.get_user.return_value.user
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=20)
    at.session_state['auth']=auth;at.session_state['main_page']='Decks';at.run()
    return at


def test_each_course_card_lists_only_its_study_decks(monkeypatch):
    at=course_app(monkeypatch)
    labels=[item.label for item in at.expander if item.label=='View all study decks']
    assert labels==['View all study decks','View all study decks']
    finance=at.expander[0]
    names=[item.value for item in finance.markdown]
    assert any('WACC basics' in name for name in names)
    assert any('Bond pricing' in name for name in names)
    assert not any('Capital structure' in name for name in names)
    empty=at.expander[1]
    assert any('No Study decks in Investments yet' in item.value for item in empty.caption)
    assert not at.exception


def test_course_deck_list_can_sort_by_recent_publication_or_name(monkeypatch):
    at=course_app(monkeypatch)
    sort=at.radio(key='course_study_sort_0')
    assert sort.value=='Recently added'
    finance=at.expander[0]
    names=[item.value for item in finance.markdown]
    assert names.index(':material/menu_book: **WACC basics**')<names.index(':material/menu_book: **Bond pricing**')
    sort.set_value('A–Z').run()
    finance=at.expander[0]
    names=[item.value for item in finance.markdown]
    assert names.index(':material/menu_book: **Bond pricing**')<names.index(':material/menu_book: **WACC basics**')


def test_study_buttons_open_study_mode_with_the_selected_deck(monkeypatch):
    copies=[]
    at=course_app(monkeypatch,copies)
    assert not any(button.key=='course_menu_0_battle_battle-cf' for button in at.button)
    at.button(key='course_study_0_study-own').click().run()
    assert at.session_state['main_page']=='Play'
    assert at.session_state['study_active'] is True
    assert at.session_state['study_choice']=='Study alone'
    assert at.session_state['study_deck_preselection']=='study-own'
    at=course_app(monkeypatch,copies)
    at.button(key='course_study_0_study-other').click().run()
    assert copies==[('copy','study-other')]
    assert at.session_state['study_deck_preselection']=='copy-1'
    assert not at.exception


def test_add_published_deck_from_search_without_starting_study(monkeypatch):
    copies = []
    at = course_app(monkeypatch, copies)
    assert at.button(key='course_studio_0_study-own').disabled
    at.text_input(key='course_study_search_0').set_value('bond').run()
    add = at.button(key='course_studio_0_study-other')
    assert add.label == 'Add to my Deck Studio'
    add.click().run()
    assert copies == [('add_to_studio','study-other')]
    assert at.session_state.main_page == 'Decks'
    assert not at.session_state.get('study_active')
    saved = at.button(key='course_studio_0_study-other')
    assert saved.disabled and saved.label == 'In my Deck Studio'
    at.text_input(key='course_study_search_0').set_value('').run()
    assert at.button(key='course_studio_0_study-other').disabled
    assert not at.exception
