from copy import deepcopy
from pathlib import Path

from test_deck_ui import deck_app

APP=(Path(__file__).parents[1]/'app.py').read_text()

FRIEND={'id':'edge1','person':{'id':'b','username':'student_b','image_path':None}}
INCOMING={'id':'edge2','person':{'id':'c','username':'student_c','image_path':None}}
SENT={'id':'edge3','person':{'id':'d','username':'student_d','image_path':None}}


def friends_page(monkeypatch,open_error=None,students=None):
    chat_calls=[];friend_calls=[]
    def friends(self,action,value=''):
        friend_calls.append((action,value))
        if action=='list':return {'code':'AB23CD45','friends':[FRIEND],'incoming':[INCOMING],'sent':[SENT],'invite_expires':None}
        return {'message':'Done.'}
    def chat(self,kind,data=None):
        chat_calls.append((kind,deepcopy(data)))
        if kind=='list':return {'threads':[]}
        if kind=='open':
            if open_error:raise ValueError(open_error)
            return {'id':'thread1'}
        if kind=='read':return {'partner':FRIEND['person'],'messages':[],'has_older':False}
        return {}
    monkeypatch.setattr('db.FriendsRepository.action',friends)
    monkeypatch.setattr('db.FriendsRepository.university_profiles',lambda self:{'university':'Nova SBE','profiles':students or []})
    monkeypatch.setattr('db.ChatRepository.action',chat)
    at=deck_app(monkeypatch)
    at.session_state['main_page']='Friends'
    return at.run(),chat_calls,friend_calls


def keys(at):
    return [str(b.key) for b in at.button]


def test_clicking_a_friend_opens_the_conversation_with_that_friend(monkeypatch):
    at,chat_calls,_=friends_page(monkeypatch)
    friend=next(b for b in at.button if b.key=='friend_chat_edge1')
    assert friend.label=='Chat'
    friend.click().run()
    assert ('open',{'user_id':'b'}) in chat_calls
    assert at.session_state['chat_open']=='thread1'
    assert any(w.label=='Message' for w in at.text_area)
    assert not at.exception


def test_pending_requests_offer_no_chat_button(monkeypatch):
    at,_,_=friends_page(monkeypatch)
    assert [k for k in keys(at) if k.startswith('friend_chat_')]==['friend_chat_edge1']


def test_failed_open_shows_an_error_and_opens_nothing(monkeypatch):
    at,_,_=friends_page(monkeypatch,open_error='You can only message friends or session partners.')
    next(b for b in at.button if b.key=='friend_chat_edge1').click().run()
    assert any('only message friends' in e.value for e in at.error)
    assert 'chat_open' not in at.session_state
    assert not at.exception


def test_friend_actions_are_visible_and_removal_keeps_a_confirmation(monkeypatch):
    at,_,friend_calls=friends_page(monkeypatch)
    labels={button.label for button in at.button}
    assert {'Battle','Study','Chat','Remove'} <= labels
    assert not any(expander.label=='Remove friend' for expander in at.expander)
    next(b for b in at.button if b.key=='remove_friend_edge1').click().run()
    next(b for b in at.button if b.key=='remove_edge1').click().run()
    assert ('remove','edge1') in friend_calls
    assert not at.exception


def test_friend_action_columns_reserve_equal_spacing_for_each_control():
    assert "battle,study,chat,remove=st.columns([1.35,1.2,.7,.7],gap='small'" in APP
    assert 'key="friend_chat_"+item["id"],icon=":material/chat:",help="Open chat with "+person["username"],use_container_width=True' in APP


def test_friend_match_actions_open_the_matching_invitation_setup(monkeypatch):
    at,_,_=friends_page(monkeypatch)
    next(button for button in at.button if button.key=='friend_battle_edge1').click().run()
    assert at.session_state['main_page']=='Play'
    assert at.session_state['play_mode_preview']=='Battle'
    assert at.session_state['battle_new_setup']
    assert at.session_state['battle_invite_friend']['id']=='b'
    at,_,_=friends_page(monkeypatch)
    next(button for button in at.button if button.key=='friend_study_edge1').click().run()
    assert at.session_state['main_page']=='Play'
    assert at.session_state['study_active']
    assert at.session_state['study_choice']=='Study together'
    assert at.session_state['study_invite_friend']['id']=='b'


def test_empty_friend_sections_use_clear_copy_without_counts(monkeypatch):
    def friends(self,action,value=''):
        if action=='list':return {'code':'AB23CD45','friends':[],'incoming':[],'sent':[],'invite_expires':'2026-12-01T12:00:00Z'}
        return {'message':'Done.'}
    monkeypatch.setattr('db.FriendsRepository.action',friends)
    monkeypatch.setattr('db.FriendsRepository.university_profiles',lambda self:{'university':'Nova SBE','profiles':[]})
    monkeypatch.setattr('db.ChatRepository.action',lambda self,kind,data=None:{'threads':[]})
    at=deck_app(monkeypatch);at.session_state['main_page']='Friends';at.run()
    assert any('No pending requests.' == item.value for item in at.caption)
    assert not any('Your current link expires' in item.value for item in at.caption)
    assert not at.exception


def test_friends_page_uses_the_compact_social_dashboard_layout(monkeypatch):
    at,_,_=friends_page(monkeypatch)
    headings={item.value for item in at.subheader}
    assert 'Find students at your university' in headings
    assert any(field.label=='Search friends' for field in at.text_input)
    assert any(button.key=='friends_find_code' and button.label=='Add' for button in at.button)
    assert {'Battle','Study'} <= {button.label for button in at.button}
    assert any(code.value=='#AB23CD45' for code in at.code)
    assert not at.exception


def test_friend_code_lookup_is_in_the_invite_card_while_search_stays_with_friends(monkeypatch):
    at,_,_=friends_page(monkeypatch)
    assert any(field.key=='friends_code_entry' for field in at.text_input)
    assert any(button.key=='friends_find_code' for button in at.button)
    assert any(field.key=='friends_local_search' for field in at.text_input)
    assert not at.exception


def test_university_directory_uses_a_compact_add_friend_row(monkeypatch):
    at,_,_=friends_page(monkeypatch,students=[{'id':'nova-1','username':'student_nova','image_path':None}])
    button=next(button for button in at.button if button.key=='university_friend_nova-1')
    assert button.label=='Add'
    assert any(caption.value=='Nova SBE' for caption in at.caption)
    assert not at.exception


def test_new_invitation_link_remains_visible_after_creation(monkeypatch):
    monkeypatch.setenv('APP_URL','https://studyduel-nova.streamlit.app')
    created=False
    def friends(self,action,value=''):
        nonlocal created
        if action=='list':
            return {'code':'AB23CD45','friends':[],'incoming':[],'sent':[],'invite_expires':'2026-12-01T12:00:00Z' if created else None}
        if action=='create_invite':
            created=True
            return {'token':'a'*48,'message':'Invitation link created.'}
        return {'message':'Done.'}
    monkeypatch.setattr('db.FriendsRepository.action',friends)
    monkeypatch.setattr('db.ChatRepository.action',lambda self,kind,data=None:{'threads':[]})
    at=deck_app(monkeypatch)
    at.session_state['main_page']='Friends';at.run()
    assert not any(expander.label in {'Add a friend by code','Invite a friend with a link'} for expander in at.expander)
    next(button for button in at.button if button.label=='New link').click().run()
    assert not at.exception
