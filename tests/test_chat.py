from copy import deepcopy
from test_deck_ui import deck_app,button


def test_dropdown_opens_private_chat_and_failed_send_keeps_draft(monkeypatch):
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
    assert any(p.proto.popover.label=='Chats (1)' for p in at.get('popover'))
    button(at,'Open chat with Demo Alex').click().run()
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


def test_study_partner_opens_the_right_chat_without_answering(monkeypatch):
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
    at,study_calls,d=setup(monkeypatch);button(at,'Start studying').click().run()
    assert any(p.proto.popover.label=='StudyPartner' for p in at.get('popover'))
    button(at,'Send friend request').click().run()
    assert ('request_user','partner') in friend_calls
    assert any(s.value=='Friend request sent.' for s in at.success)
    button(at,'Send message').click().run()
    assert ('open',{'user_id':'partner'}) in calls
    assert at.session_state.chat_open=='thread'
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
    at=deck_app(monkeypatch);at.session_state.chat_open='thread';at.run()
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
