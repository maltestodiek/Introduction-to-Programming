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


def test_play_landing_shows_only_mode_badges_and_keeps_invitations_inside_each_mode(monkeypatch):
    monkeypatch.setattr('db.play_unread_updates',lambda client,seen=():{'battle:invite:battle-invite','study:invite:study-invite'})
    monkeypatch.setattr('db.BattleRepository.action',lambda self,action,data=None:{'invites':[
        {'id':'battle-invite','incoming':True,'username':'GingerHP','deck_name':'Corporate Finance drill','course':'Corporate Finance'},
    ],'sessions':[],'search':None} if action=='list' else {})
    monkeypatch.setattr('db.StudyRepository.action',lambda self,action,data=None:{'invites':[
        {'id':'study-invite','username':'Alex','course':'Corporate Finance','language':'English','count':20},
    ],'decks':[],'shared':[],'sessions':[],'open':[],'friends':[],'feedback':[]} if action=='list' else {})
    at=deck_app(monkeypatch)
    keyed(at,'nav_Play').click().run()
    assert [h.value for h in at.subheader] == ['Battle Mode :violet-badge[1]', 'Study Mode :violet-badge[1]']
    assert not any('play-invite-notice' in item.value for item in at.markdown)
    assert not any(button.label in ('Accept','Accept invitation','Decline') for button in at.button)
    keyed(at,'choose_battle_mode').click().run()
    assert keyed(at,'battle_accept_battle-invite')
    assert at.session_state['play_mode_preview']=='Battle'
    assert not at.exception


def test_study_invitation_notice_opens_study_mode(monkeypatch):
    monkeypatch.setattr('db.BattleRepository.action',lambda self,action,data=None:{'invites':[],'sessions':[],'search':None})
    monkeypatch.setattr('db.StudyRepository.action',lambda self,action,data=None:{'invites':[
        {'id':'study-invite','username':'Alex','course':'Corporate Finance','language':'English','count':20},
    ],'decks':[],'shared':[],'sessions':[],'open':[],'friends':[],'feedback':[]})
    at=deck_app(monkeypatch)
    keyed(at,'nav_Play').click().run()
    keyed(at,'choose_study_mode').click().run()
    assert any(b.key=='study_accept_study-invite' for b in at.button)
    assert at.session_state['play_mode_preview']=='Study'
    assert not at.exception


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



def test_study_overview_explains_both_unread_items_and_keeps_them_visible_after_read(monkeypatch):
    from test_deck_ui import button
    events={'study:invite:i','study:match:m','battle:invite:b'}
    def unread(client,seen=()):
        events.difference_update(seen)
        return events.copy()
    monkeypatch.setattr('db.play_unread_updates',unread)
    monkeypatch.setattr('play_updates.visible_update',lambda key,label,summary=False:summary)
    monkeypatch.setattr('db.StudyRepository.action',lambda self,action,data=None:{
        'invites':[dict(id='i',username='Alex',course='Finance',language='English',count=20)],
        'sessions':[dict(id='m',state='paired',mode='random',name='Valuation',count=20,cursor=10)],
        'decks':[],'shared':[]})
    at=deck_app(monkeypatch)
    keyed(at,'nav_Play').click().run()
    keyed(at,'choose_study_mode').click().run()
    assert not at.exception
    copy=[e.proto.body for e in at.get('html')]
    assert any('Invitation from Alex' in line for line in copy)
    assert any('Match found · Valuation' in line for line in copy)
    assert events=={'battle:invite:b'}
    assert len([c for c in at.caption if c.value=='Seen'])==2
    keyed(at,'view_update_study:invite:i').click().run()
    assert button(at,'Accept invitation')
    assert not at.exception
