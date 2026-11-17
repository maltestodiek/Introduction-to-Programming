from pathlib import Path
from unittest.mock import Mock
from types import SimpleNamespace as Obj
from streamlit.testing.v1 import AppTest
from auth import AuthService
from logic import DEFAULT_AVATAR
from test_deck_rules import complete_deck


def deck_app(monkeypatch):
    profile={'username':'student_a','university':'Example University','courses':['Finance'],'languages':['English'],'avatar':DEFAULT_AVATAR,'image_mode':'Avatar'}
    monkeypatch.setattr('db.ProfileRepository.load',lambda self:profile)
    monkeypatch.setattr('db.DeckRepository.list',lambda self,course:[])
    client=Mock();client.auth.get_user.return_value=Obj(user=Obj(id='a'))
    auth=AuthService(client);auth.user=client.auth.get_user.return_value.user
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=20)
    at.session_state['auth']=auth;at.session_state['main_page']='Decks';at.run()
    return at

def button(at,label):return next(b for b in at.button if b.label==label)

def test_placeholders_disabled_and_incomplete_card_rejected(monkeypatch):
    at=deck_app(monkeypatch)
    assert not button(at,'Import from Anki').disabled
    assert not button(at,'Generate with AI').disabled
    assert not any(exp.label=='Battle Mode Decks' for exp in at.expander)
    assert 'Create Battle Mode Deck' in [widget.label for widget in at.button]
    assert not any('30-question' in getattr(widget,'value','') for widget in at.markdown)
    assert not at.exception

def test_active_decks_screen_does_not_offer_legacy_thirty_question_authoring(monkeypatch):
    at=deck_app(monkeypatch)
    labels=[widget.label for widget in at.button]
    assert 'Create 15-question duel deck' not in labels
    assert 'Create Battle Mode Deck' in labels
    assert not at.exception


def test_battle_deck_creator_warns_when_more_than_fifteen_cards_are_selected(monkeypatch):
    cards=[{'id':str(index),'question':f'Question {index}'} for index in range(16)]
    def action(self,kind,data=None):
        if kind=='sources':
            return {'sources':[{'id':'source-1','name':'Source','course':'Finance','language':'English','count':16,'battle_capable':True}]}
        if kind=='source':return {'name':'Source','cards':cards}
        raise AssertionError(kind)
    monkeypatch.setattr('db.BattleRepository.action',action)
    at=deck_app(monkeypatch)
    at.session_state['battle_deck_creator']=True;at.run()
    for checkbox in at.checkbox[:16]:checkbox.check().run()
    assert any('more than 15 cards' in error.value for error in at.error)
    assert button(at,'Submit Battle Deck').disabled
    assert not at.exception
