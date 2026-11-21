from pathlib import Path
from types import SimpleNamespace as Obj
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from auth import AuthService
from logic import DEFAULT_AVATAR
from test_deck_ui import deck_app

ROOT=Path(__file__).parents[1]
NAVIGATION_CSS=(ROOT/'assets'/'navigation.css').read_text()
PROFILE={'username':'student_a','university':'Example University','courses':['Finance'],'languages':['English'],'avatar':DEFAULT_AVATAR,'image_mode':'Avatar'}


def keyed(at,key):
    return next(b for b in at.button if b.key==key)


def signed_in_app(monkeypatch,profile,saved=None):
    monkeypatch.setattr('db.ProfileRepository.load',lambda self:profile)
    monkeypatch.setattr('db.DeckRepository.list',lambda self,course:[])
    if saved is not None:
        monkeypatch.setattr('launch.browser_bridge',lambda *a,**k:saved)
    client=Mock();client.auth.get_user.return_value=Obj(user=Obj(id='a'))
    auth=AuthService(client);auth.user=client.auth.get_user.return_value.user
    at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
    at.session_state['auth']=auth
    return at.run()


def test_signed_in_user_with_a_profile_lands_on_play(monkeypatch):
    at=signed_in_app(monkeypatch,PROFILE)
    assert at.title[0].value=='Play'
    assert not any(b.label=='Edit profile' for b in at.button)


def test_header_logo_opens_play_from_another_page(monkeypatch):
    at=deck_app(monkeypatch)
    assert at.session_state['main_page']=='Decks'
    keyed(at,'open_home').click().run()
    assert at.session_state['main_page']=='Play'
    assert at.title[0].value=='Play'


def test_user_without_a_profile_still_sees_profile_setup(monkeypatch):
    at=signed_in_app(monkeypatch,None)
    assert any(b.label=='Save profile' for b in at.button)
    assert not any(b.key == 'open_home' for b in at.button)
    at.text_input(key='profile_username').set_value('student_new').run()
    next(b for b in at.button if b.label == 'Save profile').click().run()
    assert at.error
    assert any(b.label == 'Save profile' for b in at.button)
    assert not any(title.value == 'Play' for title in at.title)
    assert not at.exception


@pytest.mark.parametrize('page', ['Decks', 'Chats'])
def test_returning_browser_still_resumes_its_remembered_page(monkeypatch, page):
    monkeypatch.setattr('db.ProfileRepository.load',lambda self:PROFILE)
    monkeypatch.setattr('db.DeckRepository.list',lambda self,course:[])
    saved={'started':True,'user_id':'a','page':page,'session':{'access_token':'access','refresh_token':'refresh'}}
    monkeypatch.setattr('launch.browser_bridge',lambda *a,**k:saved)
    client=Mock();client.auth.get_user.return_value=Obj(user=Obj(id='a'))
    at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
    at.session_state['auth']=AuthService(client)
    at.run()
    assert at.session_state['main_page']==page
    assert not at.exception


def test_logo_button_keeps_brand_look_and_focus_indicator():
    assert '.st-key-open_home button::before{' in NAVIGATION_CSS
    assert '.st-key-open_home button:focus-visible{outline:' in NAVIGATION_CSS
    assert '.st-key-open_home button p strong{' in NAVIGATION_CSS
