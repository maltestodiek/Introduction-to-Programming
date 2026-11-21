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


def test_play_landing_shows_only_mode_cards_and_does_not_load_sessions(monkeypatch):
    calls=[]
    monkeypatch.setattr('db.StudyRepository.action',lambda self,action,data=None:calls.append((action,data)) or {})
    at=deck_app(monkeypatch)
    button(at,'Play').click().run()
    headings=[item.value for item in at.subheader]
    assert headings.count('Battle Mode')==1 and headings.count('Study Mode')==1
    assert not any(name in headings for name in ['Your study sessions','Ongoing study sessions','Study history'])
    assert not calls
    assert not at.exception
