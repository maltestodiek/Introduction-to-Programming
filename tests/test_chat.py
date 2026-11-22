from copy import deepcopy
from test_deck_ui import deck_app,button


def test_chats_page_opens_private_chat_and_failed_send_keeps_draft(monkeypatch):
    calls=[];fail=[True]
    def action(self,kind,data=None):
        calls.append((kind,deepcopy(data)))
        if kind=='list':return {'threads':[{'id':'demo','username':'Demo Alex','image_path':None,'preview':'Ready to study?','from_me':False,'unread':1}]}
        if kind=='read':return {'partner':{'id':'other','username':'Demo Alex','image_path':None},'messages':[{'id':1,'body':'Ready to study?','created_at':'2026-11-13T12:00:00Z','from_me':False}],'has_older':False}
        if kind=='send':
            if fail[0]:raise ValueError('Please retry')
            return {'id':2}
        return {}
    monkeypatch.setattr('db.ChatRepository.action',action)
    at=deck_app(monkeypatch)
    assert not any(p.proto.popover.label.startswith('Chats') for p in at.get('popover'))
    button(at,'Chats (1)').click().run()
    assert at.title[0].value=='Chats'
    assert not any(w.label=='Message' for w in at.text_area)
    button(at,'Open chat with Demo Alex (1 unread)').click().run()
    assert any(t.value=='Ready to study?' for t in at.text)
    assert not any(p.proto.popover.label.startswith('Chats') for p in at.get('popover'))
    assert all(m.proto.avatar and m.proto.avatar != ':material/person:' for m in at.get('chat_message'))
    next(w for w in at.text_area if w.label=='Message').set_value('Hello Alex')
    button(at,'Send message').click().run()
    assert next(w for w in at.text_area if w.label=='Message').value=='Hello Alex'
    first=next(d for k,d in calls if k=='send');fail[0]=False
    button(at,'Send message').click().run()
    sent=[d for k,d in calls if k=='send'];assert sent[-1]['request_id']==first['request_id']
    assert next(w for w in at.text_area if w.label=='Message').value==''
    assert not at.exception


def test_study_round_keeps_partner_shortcuts_out_of_the_question_workspace(monkeypatch):
    from test_study_ui import setup
    calls=[]
    def action(self,kind,data=None):
        calls.append((kind,deepcopy(data)))
        if kind=='list':return {'threads':[]}
        if kind=='partner':return {'partner':{'id':'partner','username':'StudyPartner','image_path':None}}
        if kind=='open':return {'id':'thread'}
        if kind=='read':return {'partner':{'id':'partner','username':'StudyPartner','image_path':None},'messages':[],'has_older':False}
        return {}
    monkeypatch.setattr('db.ChatRepository.action',action)
    friend_calls=[]
    monkeypatch.setattr('db.FriendsRepository.action',lambda self,kind,value='':friend_calls.append((kind,value)) or {'message':'Friend request sent.'})
    at,study_calls,_=setup(monkeypatch)
    # Simulate resuming a paired session with its server-side progress available.
    monkeypatch.setattr('db.StudyRepository.progress',lambda self,session_id:{'answers':[]})
    at.session_state.study_choice='Study together'
    at.session_state.study_session='session'
    at.run()
    assert not any(p.proto.popover.label=='StudyPartner' for p in at.get('popover'))
    assert not any(button.label in ('Send friend request', 'Send message') for button in at.button)
    assert not any(kind in ('partner','open') for kind,_ in calls)
    assert friend_calls == []
    assert not any(k=='answer' for k,_ in study_calls)
    assert not at.exception


def test_chat_friend_controls_follow_relationship_state(monkeypatch):
    status={'friends':[],'incoming':[],'sent':[]};calls=[]
    def chat(self,kind,data=None):
        if kind=='list':return {'threads':[]}
        if kind=='read':return {'partner':{'id':'other','username':'Alex','image_path':None},'messages':[],'has_older':False}
        return {}
    def friends(self,kind,value=''):
        if kind=='list':return status
        calls.append((kind,value))
        status['sent']=[{'id':'edge','person':{'id':'other'}}]
        return {'message':'Friend request sent.'}
    monkeypatch.setattr('db.ChatRepository.action',chat)
    monkeypatch.setattr('db.FriendsRepository.action',friends)
    at=deck_app(monkeypatch)
    at.session_state.main_page='Chats'
    at.session_state.chat_open='thread'
    at.run()
    button(at,'Send friend request').click().run()
    assert calls==[('request_user','other')]
    assert any(c.value=='Friend request sent' for c in at.caption)
    assert not any(b.label=='Send friend request' for b in at.button)
    status['sent']=[];status['incoming']=[{'id':'incoming','person':{'id':'other'}}];at.run()
    assert button(at,'Accept friend request')
    status['incoming']=[];status['friends']=[{'id':'edge','person':{'id':'other'}}];at.run()
    assert any(c.value=='Friends' for c in at.caption)
    assert not any(b.label in ('Send friend request','Accept friend request') for b in at.button)
    assert not at.exception



def chats_with_friends(monkeypatch, *, reject_open=False, inbox_unavailable=False):
    alex = {'id': 'alex', 'username': 'Alex', 'image_path': None}
    noor = {'id': 'noor', 'username': 'Noor', 'image_path': None}
    threads = [{
        'id': 'alex-thread', 'user_id': alex['id'], 'username': alex['username'],
        'image_path': None, 'preview': 'See you later', 'from_me': True, 'unread': 0,
    }]
    calls = []

    def chat(self, kind, data=None):
        calls.append((kind, deepcopy(data)))
        if kind == 'list':
            if inbox_unavailable:
                raise ValueError('Inbox unavailable')
            return {'threads': deepcopy(threads)}
        if kind == 'open':
            assert data == {'user_id': 'noor'}
            if reject_open:
                raise ValueError('You can message friends or matched session partners')
            threads.append({
                'id': 'noor-thread', 'user_id': noor['id'], 'username': noor['username'],
                'image_path': None, 'preview': 'No messages yet', 'from_me': False, 'unread': 0,
            })
            return {'id': 'noor-thread'}
        if kind == 'read':
            peer = {'alex-thread': alex, 'noor-thread': noor}[data['id']]
            return {'partner': peer, 'messages': [], 'has_older': False}
        raise AssertionError(kind)

    relationships = {
        'friends': [{'id': 'a-edge', 'person': alex}, {'id': 'n-edge', 'person': noor}],
        'incoming': [{'person': {'id': 'pending', 'username': 'Pending', 'image_path': None}}],
        'sent': [{'person': {'id': 'invited', 'username': 'Invited', 'image_path': None}}],
    }
    monkeypatch.setattr('db.ChatRepository.action', chat)
    monkeypatch.setattr('db.FriendsRepository.action', lambda self, kind: relationships)
    at = deck_app(monkeypatch)
    button(at, 'Chats').click().run()
    return at, calls


def test_start_conversation_lists_only_friends_without_existing_threads(monkeypatch):
    at, calls = chats_with_friends(monkeypatch)
    assert button(at, 'Open chat with Alex')
    button(at, 'Start conversation').click().run()
    assert [widget.label for widget in at.button if str(widget.key).startswith('chat_start_friend_')] == ['Chat with Noor']
    assert all(kind == 'list' for kind, _ in calls)
    button(at, 'Chat with Noor').click().run()
    assert at.title[0].value == 'Chats'
    assert at.session_state.chat_open == 'noor-thread'
    assert ('open', {'user_id': 'noor'}) in calls
    assert ('read', {'id': 'noor-thread'}) in calls
    assert all(kind != 'send' for kind, _ in calls)
    assert button(at, 'Open chat with Alex')
    assert button(at, 'Open chat with Noor')
    assert any(widget.label == 'Message' for widget in at.text_area)
    button(at, 'Open chat with Alex').click().run()
    assert at.session_state.chat_open == 'alex-thread'
    assert ('read', {'id': 'alex-thread'}) in calls
    assert not at.exception


def test_rejected_start_keeps_the_friend_picker_available(monkeypatch):
    at, calls = chats_with_friends(monkeypatch, reject_open=True)
    button(at, 'Start conversation').click().run()
    button(at, 'Chat with Noor').click().run()
    assert any('message friends or matched session partners' in error.value for error in at.error)
    assert at.session_state.main_page == 'Chats'
    assert 'chat_open' not in at.session_state
    assert button(at, 'Chat with Noor')
    assert not any(kind in ('read', 'send') for kind, _ in calls)
    assert not at.exception


def test_inbox_unavailable_does_not_offer_unchecked_friends(monkeypatch):
    at, calls = chats_with_friends(monkeypatch, inbox_unavailable=True)
    assert button(at, 'Start conversation').disabled
    assert any('conversations' in error.value.lower() for error in at.error)
    assert all(kind == 'list' for kind, _ in calls)
    assert not at.exception
