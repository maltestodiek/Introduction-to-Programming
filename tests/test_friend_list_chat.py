from copy import deepcopy

from test_deck_ui import deck_app

FRIEND={'id':'edge1','person':{'id':'b','username':'student_b','image_path':None}}
INCOMING={'id':'edge2','person':{'id':'c','username':'student_c','image_path':None}}
SENT={'id':'edge3','person':{'id':'d','username':'student_d','image_path':None}}


def friends_page(monkeypatch,open_error=None):
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
    monkeypatch.setattr('db.ChatRepository.action',chat)
    at=deck_app(monkeypatch)
    at.session_state['main_page']='Friends'
    return at.run(),chat_calls,friend_calls


def keys(at):
    return [str(b.key) for b in at.button]


def test_clicking_a_friend_opens_the_conversation_with_that_friend(monkeypatch):
    at,chat_calls,_=friends_page(monkeypatch)
    friend=next(b for b in at.button if b.key=='friend_chat_edge1')
    assert friend.label=='student_b'
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


def test_remove_friend_still_works_from_the_same_entry(monkeypatch):
    at,_,friend_calls=friends_page(monkeypatch)
    next(b for b in at.button if b.key=='remove_edge1').click().run()
    assert ('remove','edge1') in friend_calls
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
    next(button for button in at.button if button.label=='Create new invitation link').click().run()
    assert any('https://studyduel-nova.streamlit.app/?invite=' in code.value for code in at.code)
    assert any(item.value=='Your invitation link' for item in at.subheader)
    assert not at.exception
