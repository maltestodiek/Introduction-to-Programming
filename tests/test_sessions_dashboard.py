from datetime import datetime, timedelta, timezone

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
    {'id':'s-together','name':'CF Financial Restructuring questions','mode':'friend','state':'paired','count':20,'cursor':1,'deadline':SOON},
    {'id':'s-solo','name':'CF Financial Restructuring questions','mode':'solo','state':'own','count':10,'cursor':6},
    {'id':'s-done','name':'Market efficience questions','mode':'solo','state':'completed','count':17,'cursor':17},
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
    assert [(row['result'],row['mode'],row['score'],row['xp']) for row in rows]==[('Win','vs Vincent_bcm','15/15','+40'),('Loss','vs malte','9/15','+0'),('Done','Solo','17/17','–')]
    assert battle_record(BATTLES)=={'wins':1,'losses':1,'draws':0}


def dashboard(monkeypatch,battles=BATTLES,study=STUDY,calls=None):
    calls=[] if calls is None else calls
    monkeypatch.setattr('db.BattleRepository.action',lambda self,action,data=None:{'sessions':list(battles),'invites':[],'search':None} if action=='list' else {})
    def study_action(self,action,data=None):
        calls.append((action,data))
        if action=='list':return {'decks':[],'shared':[],'sessions':list(study),'open':[],'invites':[],'friends':[],'feedback':[]}
        return {}
    monkeypatch.setattr('db.StudyRepository.action',study_action)
    at=deck_app(monkeypatch)
    button(at,'Play').click().run()
    return at


def text_of(at):
    return ' '.join([item.value for item in at.markdown]+[item.value for item in at.caption])


def test_dashboard_shows_continue_banner_ongoing_cards_history_and_stats(monkeypatch):
    at=dashboard(monkeypatch)
    headings=[item.value for item in at.subheader]
    assert 'Ongoing study sessions' in headings and 'Study history' in headings
    text=text_of(at)
    assert 'Continue where you left off' in text
    assert 'Study together' in text and 'Study sessions finished' in text
    assert 'Battle record' not in text and 'Battle XP from these Battles' not in text and 'Win streak' not in text
    assert not at.exception


def test_existing_session_actions_still_work(monkeypatch):
    at=dashboard(monkeypatch)
    at.button(key='continue_session').click().run()
    assert at.session_state['study_session']=='s-together'
    at=dashboard(monkeypatch)
    at.button(key='home_study_s-solo').click().run()
    assert at.session_state['study_session']=='s-solo'
    at=dashboard(monkeypatch);at.button(key='history_study_s-done').click().run()
    assert at.session_state['study_session']=='s-done'


def test_dashboard_keeps_battle_sessions_outside_the_play_page(monkeypatch):
    at=dashboard(monkeypatch)
    keys=[getattr(item,'key','') or '' for item in at.button]
    assert 'home_battle_b-ongoing' not in keys and 'history_battle_review_b-win' not in keys
    assert 'home_study_s-solo' in keys and 'history_study_s-done' in keys


def test_history_shows_five_rows_and_more_on_request(monkeypatch):
    many=[{**STUDY[2],'id':f's-{index}'} for index in range(7)]
    at=dashboard(monkeypatch,battles=BATTLES,study=many)
    keys=lambda:[getattr(item,'key','') or '' for item in at.button if (getattr(item,'key','') or '').startswith('history_study_')]
    assert len(keys())==5
    button(at,'Show more').click().run()
    assert len(keys())==7


def test_empty_dashboard_invites_to_start(monkeypatch):
    at=dashboard(monkeypatch,battles=[],study=[])
    text=text_of(at)
    assert 'No ongoing sessions' in text and 'No finished sessions yet' in text
    assert not at.exception
