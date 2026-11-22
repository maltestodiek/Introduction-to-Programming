from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from logic import battle_record, session_continue_pick, session_history_rows, time_left_text
from test_deck_ui import button, deck_app

NOW=datetime(2026,11,19,12,0,tzinfo=timezone.utc)
SOON=(NOW+timedelta(hours=6,minutes=10)).isoformat()

BATTLES=[
    {'id':'b-ongoing','deck_name':'Market efficience questions','course':'Corporate Finance','language':'English','status':'ongoing','started':True},
    {'id':'b-pending','deck_name':'CF Financial Restructuring questions','course':'Corporate Finance','language':'English','status':'pending','started':True},
    {'id':'b-win','deck_name':'CF Financial Restructuring questions','course':'Corporate Finance','language':'English','status':'completed','result':'win','score':15,'opponent_score':9,'game_xp_delta':40,'opponent_username':'Vincent_bcm'},
    {'id':'b-loss','deck_name':'Bonds speed round','course':'Corporate Finance','language':'English','status':'completed','result':'loss','score':9,'opponent_score':12,'game_xp_delta':0,'opponent_username':'malte'},
]
STUDY=[
    {'id':'s-together','name':'CF Financial Restructuring questions','course':'Corporate Finance','language':'English','mode':'friend','state':'paired','count':20,'cursor':1,'deadline':SOON},
    {'id':'s-solo','name':'CF Financial Restructuring questions','mode':'solo','state':'own','count':10,'cursor':6},
    {'id':'s-done','name':'Market efficience questions','mode':'solo','state':'completed','count':17,'cursor':17,'score':9},
]


def test_continue_prefers_a_together_session_with_the_nearest_deadline():
    pick=session_continue_pick(BATTLES,STUDY)
    assert (pick['kind'],pick['session']['id'])==('study','s-together')
    assert session_continue_pick(BATTLES,[STUDY[1]])['session']['id']=='b-ongoing'
    assert session_continue_pick([BATTLES[1]],[STUDY[1]])['session']['id']=='s-solo'
    assert session_continue_pick([BATTLES[1]],[]) is None


def test_time_left_is_rounded_for_people():
    assert time_left_text(SOON,NOW)=='6 h left'
    assert time_left_text((NOW+timedelta(minutes=40)).isoformat(),NOW)=='40 min left'
    assert time_left_text((NOW+timedelta(days=2,hours=3)).isoformat(),NOW)=='2 d left'
    assert time_left_text((NOW-timedelta(minutes=1)).isoformat(),NOW)=='Deadline passed'
    assert time_left_text(None,NOW) is None


def test_history_rows_and_battle_record():
    rows=session_history_rows([b for b in BATTLES if b['status']=='completed'],[STUDY[2]])
    assert [(row['result'],row['mode'],row['score'],row['xp']) for row in rows]==[('Win','vs Vincent_bcm','15/15','+40'),('Loss','vs malte','9/15','+0'),('Done','Solo','9/17','–')]
    assert battle_record(BATTLES)=={'wins':1,'losses':1,'draws':0}


def test_play_landing_uses_only_notification_counts_without_loading_session_lists(monkeypatch):
    at=deck_app(monkeypatch)
    # The invitation list also returns saved sessions, even when there are no invites.
    study_action=Mock(return_value={'invites': [], 'sessions': STUDY})
    monkeypatch.setattr('db.StudyRepository.action', study_action)
    button(at,'Play').click().run()

    study_action.assert_not_called()
    headings=[item.value for item in at.subheader]
    assert headings == ['Battle Mode', 'Study Mode']
    assert not any(b.label in ('Resume', 'View Study session') for b in at.button)
    assert not at.exception


def test_timed_out_study_match_shows_a_loss_in_completed_history():
    session = dict(id='study', name='Finance', mode='friend', state='completed',
                   result='Loss', cursor=10, count=20)
    row, = session_history_rows([], [session])
    assert (row['result'], row['tone']) == ('Loss', 'red')


def test_study_dashboard_shows_each_active_session_once_and_labels_history(monkeypatch):
    at=deck_app(monkeypatch)
    waiting=dict(STUDY[0], id='s-wait', mode='random', state='waiting', deadline=None)
    partner_pending=dict(STUDY[0], id='s-partner', state='waiting_for_finish', cursor=20, score=12)
    finished=dict(STUDY[0], id='s-finished', state='completed', result='Win')
    monkeypatch.setattr('db.StudyRepository.action', Mock(return_value={
        'invites': [], 'sessions': [*STUDY, waiting, partner_pending, finished], 'decks': [], 'shared': [],
    }))
    button(at,'Play').click().run()
    button(at,'Study Mode').click().run()
    assert not at.exception
    assert [tab.label for tab in at.tabs] == ['Your turn', 'Waiting', 'Completed', 'Invitations']
    assert [b.key for b in at.tabs[1].button if b.key and b.key.startswith('home_study_')] == ['home_study_s-wait','home_study_s-partner']
    assert [b.key for b in at.button if b.label in ('Resume Study', 'Open Study', 'Resume')] == [
        'home_study_s-together', 'home_study_s-solo', 'home_study_s-wait','home_study_s-partner']
    badges=[m.value for m in at.markdown if '-badge[' in m.value]
    assert sum('Study alone' in badge for badge in badges)==2
    assert sum('Study together' in badge for badge in badges)==4
    assert any(c.value=='Corporate Finance · English · 20 questions' for c in at.caption)

    for mode, expected in [
        ('Study alone', {'s-solo'}),
        ('Study together', {'s-together'}),
    ]:
        button(at,mode).click().run()
        assert not at.exception
        assert {b.key.removeprefix('study_resume_') for b in at.button
                if (b.key or '').startswith('study_resume_')} == expected
        assert not at.tabs
        assert not any(b.label == 'View Study session' for b in at.button)
        assert 'Create a new study session' in [h.value for h in at.subheader]
        button(at,'Change study mode').click().run()
        assert not any(b.label == 'Back to Play mode selection' for b in at.button)
        button(at,'Play').click().run()
        button(at,'Study Mode').click().run()

def test_history_uses_saved_score_and_returns_to_history_after_question_review(monkeypatch):
    from db import StudyRepository, ChatRepository
    session = dict(STUDY[0], state='completed', cursor=20, score=12, result='Win')
    def action(repo, name, data=None):
        if name == 'list':
            return {'sessions':[session], 'decks':[], 'shared':[], 'invites':[], 'open':[]}
        if name == 'round':
            return {'state':'completed','result':'Win','score':12,'opponent_score':9,'total':20}
        raise AssertionError(name)
    monkeypatch.setattr(StudyRepository,'action',action)
    monkeypatch.setattr(StudyRepository,'progress',lambda self,sid:{
        'answers':[{'index':0,'correct':False}],'review':[
            {'index':0,'correct':False,'question':'Which rate?', 'selected':'Ten','solution':'Five'}]})
    monkeypatch.setattr(ChatRepository,'action',lambda self,name,data=None:
        {'partner':{'id':'other','username':'Alex'}} if name=='partner' else {'threads':[]})
    at=deck_app(monkeypatch)
    button(at,'Play').click().run()
    button(at,'Study Mode').click().run()
    assert any('12/20' in m.value for m in at.markdown)
    assert not any(c.value=='XP' for c in at.caption)
    assert not any('Alex' in pop.proto.popover.label for pop in at.get('popover'))
    assert button(at,'Add Alex as a friend').proto.icon == ':material/person_add:'
    assert button(at,'Message Alex').proto.icon == ':material/chat:'
    button(at,'View Study session').click().run()
    assert any('Incorrect' in e.label and 'Which rate?' in e.label for e in at.expander)
    assert any('Ten' in m.value for m in at.markdown)
    assert any('Five' in m.value for m in at.markdown)
    button(at,'Back to Study history').click().run()
    assert 'Completed' in [t.label for t in at.tabs]
    assert not at.exception

def test_study_card_actions_target_the_displayed_partner(monkeypatch):
    from db import StudyRepository, ChatRepository, FriendsRepository
    session=dict(STUDY[0], state='waiting_for_finish', cursor=20)
    monkeypatch.setattr(StudyRepository,'action', lambda self,action,data=None:
        {'sessions':[session], 'invites':[], 'decks':[], 'shared':[]})
    partner={'username':'Alex','id':'other'}
    sent=[]
    def friends(self,action,value=''):
        if action=='list':return {'friends':[], 'sent':[{'person':partner}] if sent else [], 'incoming':[]}
        sent.append((action,value))
        return {'message':'Friend request sent.'}
    def chats(self,action,data=None):
        if action=='partner':return {'partner':partner}
        if action=='open':
            assert data == {'user_id':'other'}
            return {'id':'alex-thread'}
        if action=='read':return {'partner':partner,'messages':[],'has_older':False}
        return {'threads':[]}
    monkeypatch.setattr(FriendsRepository,'action',friends)
    monkeypatch.setattr(ChatRepository,'action',chats)
    at=deck_app(monkeypatch)
    button(at,'Play').click().run()
    button(at,'Study Mode').click().run()
    button(at,'Add Alex as a friend').click().run()
    assert sent==[('request_user','other')]
    assert button(at,'Friend request sent to Alex').disabled
    button(at,'Message Alex').click().run()
    assert at.session_state.chat_open=='alex-thread'
    assert at.session_state.main_page=='Chats' and not at.exception
