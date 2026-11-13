from copy import deepcopy
from test_deck_ui import deck_app,button

DECK={'id':'deck1','name':'Finance practice','language':'English'}
EMPTY={'queue':None,'paused':False,'invites':[],'duels':[]}

def setup(monkeypatch,friend=None,state=None):
    calls=[]
    def action(self,kind,data=None):
        calls.append((kind,data))
        if kind=='list':return deepcopy(state or EMPTY)
        if kind=='friend_options':return {'friends':[friend] if friend else []}
        return {'message':'Saved'}
    monkeypatch.setattr('db.PlayRepository.action',action)
    at=deck_app(monkeypatch)
    monkeypatch.setattr('db.DeckRepository.list',lambda self,c:[DECK])
    # The classic lobby is no longer in Play navigation. Keep its existing
    # safety checks through an isolated test-only rendering of the retained helper.
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    root=Path(__file__).parents[1]
    source=(root/'app.py').read_text().replace('Path(__file__).parent',f'Path({str(root)!r})')
    source=source.replace('        ongoing_sessions(client)\n','        ongoing_sessions(client)\n        play_lobby(client,profile)\n')
    auth=at.session_state['auth']
    at=AppTest.from_string(source,default_timeout=20)
    at.session_state['auth']=auth;at.session_state['main_page']='Play';at.run()
    return at,calls

def test_play_is_real_lobby_with_one_hour_opt_in(monkeypatch):
    at,calls=setup(monkeypatch)
    next(r for r in at.radio if r.label=='Opponent').set_value('Random player').run()
    assert any('one hour' in w.value for w in at.markdown)
    assert not any(a=='join' for a,_ in calls)
    button(at,'Find random player').click().run()
    assert ('join',{'deck_id':'deck1'}) in calls
    assert not at.exception

def test_missing_course_warning_requires_confirmation(monkeypatch):
    at,calls=setup(monkeypatch,{'id':'f','username':'Friend','has_course':False,'speaks_language':True})
    assert button(at,'Send duel invitation').disabled
    next(c for c in at.checkbox if c.label=='Invite anyway').check().run()
    button(at,'Send duel invitation').click().run()
    assert ('invite',{'deck_id':'deck1','friend_id':'f','confirm_missing_course':True}) in calls
    assert not at.exception

def test_language_mismatch_disables_friend_invite(monkeypatch):
    at,calls=setup(monkeypatch,{'id':'f','username':'Friend','has_course':True,'speaks_language':False})
    assert button(at,'Send duel invitation').disabled
    assert any('language' in w.value for w in at.warning)

def test_round_answers_and_navigation_confirmation(monkeypatch):
    at,calls=setup(monkeypatch)
    def action(self,kind,data=None):
        calls.append((kind,data))
        if kind=='round':return {'state':'question','index':0,'seconds':28,'question':'Which answer?','options':[{'id':str(i),'text':f'Choice {i}'} for i in range(4)]}
        if kind=='abandon':return {'state':'completed'}
        if kind=='answer':return {'state':'feedback','feedback':{'index':0,'correct':True,'timed_out':False,'answer_id':'0'},'card':{'question':'Which answer?','correct_answer_id':'0','answers':[{'id':str(i),'text':f'Choice {i}'} for i in range(4)]}}
        return deepcopy(EMPTY)
    monkeypatch.setattr('db.PlayRepository.action',action)
    at.session_state['play_duel']='duel1';at.run()
    button(at,'Choice 0').click().run()
    assert any('Correct' in s.value for s in at.success)
    assert ('answer',{'duel_id':'duel1','index':0,'answer_id':'0'}) in calls
    button(at,'Profile').click().run()
    assert button(at,'Confirm abandonment')
    assert not any(a=='abandon' for a,_ in calls)
    button(at,'Stay in round').click().run()
    assert at.session_state['main_page']=='Play'
    button(at,'Decks').click().run();button(at,'Confirm abandonment').click().run()
    assert ('abandon',{'duel_id':'duel1','confirmed':True}) in calls
    assert at.session_state['main_page']=='Decks'
    assert not at.exception

def test_rating_is_required_for_each_deck(monkeypatch):
    at,calls=setup(monkeypatch)
    def action(self,kind,data=None):
        calls.append((kind,data))
        if kind=='round':return {'state':'rating','score':22,'decks':[DECK,{'id':'deck2','name':'Other deck'}]}
        if kind=='finish':return {'state':'finished'}
        if kind=='friend_options':return {'friends':[]}
        return deepcopy(EMPTY)
    monkeypatch.setattr('db.PlayRepository.action',action)
    at.session_state['play_duel']='duel1';at.run()
    assert button(at,'Finish round').disabled
    at.radio[0].set_value('up').run();assert button(at,'Finish round').disabled
    at.radio[1].set_value('neutral').run();button(at,'Finish round').click().run()
    assert ('finish',{'duel_id':'duel1','ratings':{'deck1':'up','deck2':'neutral'}}) in calls
    assert not at.exception
