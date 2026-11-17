from datetime import date
import pytest
from study_plan import (study_days,remaining_steps,plan_progress,workload,validate_plan,plan_sessions,
                        session_minutes,plan_ics,course_days,plan_schedule,course_outlook,DEFAULT_TIMES)

TODAY=date(2026,11,16)  # a Monday
DECKS={'Finance':[{'id':'d1','name':'Returns'},{'id':'d2','name':'Bonds'}],'Investments':[{'id':'d3','name':'CAPM'}]}


def plan(**changes):
    p={'name':'Winter exams','target':2,'sessions':2,'times':['09:00','14:00'],'weekdays_off':[5,6],'dates_off':[],
       'courses':[{'course':'Finance','end':'2026-11-27','decks':['d1']},{'course':'Investments','end':'2026-12-04','decks':['d3']}]}
    p.update(changes);return p


def test_study_days_skip_excluded_weekdays_and_single_dates():
    days=study_days(TODAY,date(2026,11,27),[5,6],['2026-11-18'])
    assert len(days)==9 and date(2026,11,18) not in days
    assert all(d.weekday()<5 for d in days) and days[0]==TODAY and days[-1]==date(2026,11,27)
    assert study_days(TODAY,date(2026,11,15),[],[])==[]


def test_steps_count_levels_missing_to_target_not_questions():
    assert remaining_steps([None]*30,2)==60
    assert remaining_steps([0,1,2,3],2)==3
    assert remaining_steps([3,3],3)==0


def test_progress_counts_partial_levels_and_caps_at_target():
    assert plan_progress([1]*10,2)==0.5
    assert plan_progress([3,3],2)==1.0
    assert plan_progress([None,0,2,1],2)==0.375
    assert plan_progress([],2)==0.0


def test_workload_divides_steps_over_days_and_sessions_and_recalculates():
    assert workload([None]*300,2,10,1)=={'steps':600,'per_day':60,'per_session':60,'days':10,'needed':10}
    assert workload([None]*300,2,9,2)=={'steps':600,'per_day':67,'per_session':34,'days':9,'needed':9}
    assert workload([2]*30,2,9,2)=={'steps':0,'per_day':0,'per_session':0,'days':9,'needed':0}
    assert workload([None]*30,2,0,1)=={'steps':60,'per_day':60,'per_session':60,'days':0,'needed':1}


def test_at_least_20_questions_per_day_so_small_plans_finish_early():
    assert workload([None]*30,2,10,1)=={'steps':60,'per_day':20,'per_session':20,'days':10,'needed':3}
    assert workload([None]*30,2,10,3)['per_session']==7
    assert workload([1]*12,2,10,2)=={'steps':12,'per_day':12,'per_session':6,'days':10,'needed':1}
    assert workload([None]*30,2,10,1,minimum=1)['per_day']==6


def test_valid_plan_is_cleaned_and_keeps_course_specific_end_dates():
    clean=validate_plan(plan(),['Finance','Investments'],DECKS,TODAY)
    assert [c['end'] for c in clean['courses']]==['2026-11-27','2026-12-04']
    assert [c['start'] for c in clean['courses']]==[None,None]
    later=plan();later['courses'][1]['start']='2026-11-30'
    clean_later=validate_plan(later,['Finance','Investments'],DECKS,TODAY)
    assert clean_later['courses'][1]['start']=='2026-11-30' and course_days(clean_later,clean_later['courses'][1],TODAY)[0]==date(2026,11,30)
    assert len(course_days(clean_later,clean_later['courses'][0],TODAY))==10
    assert clean['times']==['09:00','14:00'] and clean['weekdays_off']==[5,6]
    assert validate_plan(plan(sessions=3,times=[]),['Finance','Investments'],DECKS,TODAY)['times']==DEFAULT_TIMES


@pytest.mark.parametrize('changes,message',[
    ({'name':'  '},'name'),
    ({'target':4},'level'),
    ({'sessions':4},'sessions'),
    ({'times':['09:00','25:00']},'time'),
    ({'times':['14:00','09:00']},'order'),
    ({'courses':[]},'course'),
    ({'courses':[{'course':'Marketing','end':'2026-11-27','decks':['d1']}]},'profile'),
    ({'courses':[{'course':'Finance','end':'2026-11-27','decks':['d3']}]},'deck'),
    ({'courses':[{'course':'Finance','end':'2026-11-27','decks':[]}]},'deck'),
    ({'courses':[{'course':'Finance','end':'2026-11-15','decks':['d1']}]},'past'),
    ({'courses':[{'course':'Finance','end':'2026-11-27','decks':['d1']},{'course':'Finance','end':'2026-11-28','decks':['d2']}]},'once'),
    ({'weekdays_off':[0,1,2,3,4,5,6]},'study day'),
    ({'courses':[{'course':'Finance','start':'2026-11-28','end':'2026-11-27','decks':['d1']}]},'start date'),
    ({'weekdays_off':[0,1,2,3,4],'courses':[{'course':'Finance','end':'2026-11-20','decks':['d1']}]},'study day'),
])
def test_rejected_plans_name_the_problem(changes,message):
    with pytest.raises(ValueError,match=message):validate_plan(plan(**changes),['Finance','Investments'],DECKS,TODAY)


def test_sessions_spread_each_course_until_its_own_end_date():
    clean=validate_plan(plan(),['Finance','Investments'],DECKS,TODAY)
    sessions=plan_sessions(clean,{'Finance':[None]*150,'Investments':[1]*5},TODAY)
    assert sum(s['steps'] for s in sessions)==300+5
    assert {s['time'] for s in sessions}<={'09:00','14:00'}
    finance=[s for s in sessions if 'Finance' in s['courses']]
    assert max(s['date'] for s in finance)<=date(2026,11,27)
    assert all(s['date'].weekday()<5 and s['steps']>0 for s in sessions)
    first=[s for s in sessions if s['date']==TODAY]
    assert sum(s['courses'].get('Finance',0) for s in first)==30  # 300 steps over 10 study days
    assert sum(s['courses'].get('Investments',0) for s in first)==1  # the plan already has more than 20 that day
    small=plan_sessions(clean,{'Finance':[None]*30,'Investments':[]},TODAY)
    assert sorted({s['date'] for s in small})==[date(2026,11,16),date(2026,11,17),date(2026,11,18)]  # 60 steps at 20 a day
    assert sessions==sorted(sessions,key=lambda s:(s['date'],s['time']))


def test_minimum_of_20_per_day_applies_to_the_whole_plan():
    clean=validate_plan(plan(),['Finance','Investments'],DECKS,TODAY)
    schedule=plan_schedule(clean,{'Finance':[None]*25,'Investments':[None]*45},TODAY)  # 50 and 90 steps: 5 and 6 a day
    assert schedule[TODAY]=={'Finance':14,'Investments':6}  # topped up to 20 from the course that ends first
    assert all(sum(day.values())==20 for day in list(schedule.values())[:-1]) and sum(sum(day.values()) for day in schedule.values())==140
    assert len(schedule)==7 and course_outlook(schedule,'Finance')=={'first':TODAY,'finish':date(2026,11,19),'days':4,'per_day':14}
    assert course_outlook(schedule,'Investments')['finish']==date(2026,11,24)
    big=plan_schedule(clean,{'Finance':[None]*150,'Investments':[None]*150},TODAY)
    assert big[TODAY]=={'Finance':30,'Investments':20}  # above the minimum: even shares, no top-up
    assert course_outlook(plan_schedule(clean,{'Finance':[2]*5,'Investments':[]},TODAY),'Finance') is None


def test_calendar_length_is_15_seconds_per_step_with_15_minute_minimum():
    assert session_minutes(1)==15 and session_minutes(60)==15 and session_minutes(61)==16 and session_minutes(240)==60


def test_calendar_file_lists_every_session_with_stable_ids():
    clean=validate_plan(plan(),['Finance','Investments'],DECKS,TODAY);clean['id']='plan-1'
    sessions=plan_sessions(clean,{'Finance':[None]*9,'Investments':[1]*5},TODAY)
    text=plan_ics(clean,sessions)
    assert text.startswith('BEGIN:VCALENDAR\r\n') and text.endswith('END:VCALENDAR\r\n')
    assert text.count('BEGIN:VEVENT')==len(sessions)
    assert 'DTSTART:20261116T090000' in text and 'UID:plan-1-20261116-0900@studyduel' in text
    assert 'SUMMARY:UniArena: Winter exams' in text
    assert plan_ics(clean,sessions)==text


def test_todays_sessions_stay_fixed_all_day_and_fill_in_order():
    from study_plan import day_snapshot,today_sessions
    clean=validate_plan(plan(courses=[{'course':'Finance','end':'2026-11-27','decks':['d1']}]),['Finance'],DECKS,TODAY)
    start={'Finance':[None]*150}  # 300 steps over 10 study days: 30 today, 15 per session
    clean['day']=day_snapshot(clean,start,TODAY)
    assert clean['day']=={'date':'2026-11-16','planned':{'Finance':30},'open':{'Finance':300}}
    assert [(s['name'],s['time'],s['planned'],s['open'],s['courses']) for s in today_sessions(clean,start,TODAY)]==[('Morning','09:00',15,15,{'Finance':15}),('Afternoon','14:00',15,15,{'Finance':15})]
    after_morning={'Finance':[1]*15+[None]*135}  # 15 steps earned
    assert [(s['open'],s['courses']) for s in today_sessions(clean,after_morning,TODAY)]==[(0,{}),(15,{'Finance':15})]
    partly={'Finance':[1]*20+[None]*130}
    assert [s['open'] for s in today_sessions(clean,partly,TODAY)]==[0,10]
    done={'Finance':[1]*40+[None]*110}  # more than planned today: nothing is added the same day
    assert [s['open'] for s in today_sessions(clean,done,TODAY)]==[0,0]
    # the next day starts from what is really left: 300-20=280 steps over 9 study days
    tomorrow=date(2026,11,17)
    assert [s['open'] for s in today_sessions(clean,partly,tomorrow)]==[16,16]
    off=validate_plan(plan(weekdays_off=[0],courses=[{'course':'Finance','end':'2026-11-27','decks':['d1']}]),['Finance'],DECKS,TODAY)
    assert today_sessions(off,start,TODAY)==[]


def test_session_is_overdue_once_its_part_of_the_day_is_over():
    from datetime import time
    from study_plan import session_overdue
    assert not session_overdue('09:00',time(11,59)) and session_overdue('09:00',time(12,0)) and session_overdue('07:30',time(23,0))
    assert not session_overdue('14:00',time(16,59)) and session_overdue('14:00',time(17,0))
    assert not session_overdue('19:00',time(23,59)) and not session_overdue('14:00',time(8,0))
