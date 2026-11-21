from copy import deepcopy
from datetime import date,timedelta
from test_deck_ui import deck_app,button


def setup(monkeypatch,plans=None,levels=(None,)*30):
    calls=[];stored=list(plans or [])
    cards=[{'id':str(i),'level':level} for i,level in enumerate(levels)]
    def study(self,action,data=None):
        if action=='list':return {'decks':[{'id':'d1','name':'Returns','course':'Finance','language':'English','count':len(cards)}],'shared':[{'id':'s1','name':'Bonds','course':'Finance','language':'English','count':len(cards)}],'sessions':[],'open':[],'invites':[],'friends':[],'feedback':[]}
        if action=='deck':return {'id':data['id'],'cards':deepcopy(cards)}
        if action=='start':
            calls.append(('study:start',deepcopy(data)));return {'id':'session-1'}
        if action=='round':return {'state':'question','index':0,'total':20,'question':'Dummy question','chapter':'Part 1','options':[{'id':'a','text':'Answer A'}],'part':'Solo study','allow_calculator':False}
        return {}
    def plans_action(self,action,data=None):
        if action=='save' and 'id' in data and 'day' in data['plan']:
            # the once-a-day snapshot of today's amount, recorded apart from saves the student makes
            calls.append(('day',deepcopy(data)));next(p for p in stored if p['id']==data['id'])['plan']=deepcopy(data['plan']);return {'id':data['id']}
        calls.append((action,deepcopy(data)))
        if action=='list':return {'plans':deepcopy(stored)}
        if action=='save':
            if 'id' in data:next(p for p in stored if p['id']==data['id'])['plan']=deepcopy(data['plan'])
            else:stored.append({'id':'plan-1','plan':data['plan'],'calendar_events':[]})
            return {'id':data.get('id','plan-1')}
        if action=='delete':
            stored.clear();return {'id':data['id']}
        return {}
    monkeypatch.setattr('db.StudyRepository.action',study)
    monkeypatch.setattr('study_plan.session_overdue',lambda time,now:False)  # labels must not depend on when the tests run
    monkeypatch.setattr('db.StudyPlanRepository.action',plans_action)
    at=deck_app(monkeypatch);button(at,'Study Plan').click().run()
    return at,calls


def widget(items,label):return next(w for w in items if w.label==label)



def test_create_plan_shows_workload_and_saves_only_on_save(monkeypatch):
    at,calls=setup(monkeypatch)
    assert at.title[0].value=='Study Plan' and any('No study plans yet' in c.value for c in at.caption)
    button(at,'Create study plan').click().run()
    assert button(at,'Save study plan').disabled
    widget(at.text_input,'Plan name').set_value('Winter exams').run()
    assert widget(at.multiselect,'Courses').options==['Finance']
    widget(at.multiselect,'Courses').set_value(['Finance']).run()
    assert button(at,'Save study plan').disabled
    end=date.today()+timedelta(days=9)
    widget(at.date_input,'Finish by (exam or target date)').set_value(end).run()
    assert widget(at.multiselect,'Decks to study').options==['Returns · 30 questions','Bonds (shared with me) · 30 questions']
    widget(at.multiselect,'Decks to study').set_value(['d1']).run()
    assert any('**20 questions per day**' in m.value and 'on 3 study days' in m.value and '7 days before your target date' in m.value for m in at.markdown)
    assert button(at,'Level 1') and button(at,'Level 2') and button(at,'Level 3')
    button(at,'Level 2').click().run()
    button(at,'2').click().run()
    assert [w.label for w in at.time_input]==['Session 1 starts at','Session 2 starts at']
    assert any('**20 questions per day**, 10 per session' in m.value for m in at.markdown)
    assert any('A session is one sitting' in c.value for c in at.caption)
    assert not any(a=='save' for a,_ in calls)
    button(at,'Save study plan').click().run()
    saved=next(v for a,v in calls if a=='save')
    assert saved=={'plan':{'name':'Winter exams','target':2,'sessions':2,'times':['09:00','14:00'],'weekdays_off':[],'dates_off':[],'courses':[{'course':'Finance','start':None,'end':end.isoformat(),'decks':['d1']}]}}
    assert any(s.value=='Study plan saved: Winter exams' for s in at.subheader) and not any(b.label=='Edit' for b in at.button)
    assert any(b.label=='Calendar file' for b in at.get('download_button')) and any('**20 questions per day**' in m.value for m in at.markdown)
    button(at,'Finish').click().run()
    assert any(s.value=='Winter exams' for s in at.subheader) and button(at,'Edit') and button(at,'Create study plan')
    assert any('Finance 0%' in str(p.proto.text) for p in at.get('progress'))
    assert not any(b.label=='Calendar file' for b in at.get('download_button')) and not any(b.label=='Confirm deletion' for b in at.button)
    assert not at.exception


def test_cancel_and_unsaved_edit_change_nothing(monkeypatch):
    end=(date.today()+timedelta(days=9)).isoformat()
    existing={'id':'plan-1','plan':{'name':'Winter exams','target':2,'sessions':1,'times':['09:00'],'weekdays_off':[],'dates_off':[],'courses':[{'course':'Finance','end':end,'decks':['d1']}]},'calendar_events':[]}
    at,calls=setup(monkeypatch,[existing],levels=(1,)*10)
    assert any('Finance 50%' in str(p.proto.text) for p in at.get('progress'))
    button(at,'Edit').click().run()
    assert widget(at.text_input,'Plan name').value=='Winter exams'
    widget(at.text_input,'Plan name').set_value('Changed').run()
    button(at,'Sa').click().run();button(at,'Su').click().run()
    button(at,'Cancel').click().run()
    assert not any(a in ('save','delete','events') for a,_ in calls)
    assert any(s.value=='Winter exams' for s in at.subheader)
    button(at,'Edit').click().run()
    assert widget(at.text_input,'Plan name').value=='Winter exams' and button(at,'Sa') and button(at,'Su')
    assert not at.exception


def test_direct_weekday_buttons_are_saved_as_days_off(monkeypatch):
    end=(date.today()+timedelta(days=9)).isoformat()
    existing={'id':'plan-1','plan':{'name':'Winter exams','target':2,'sessions':1,'times':['09:00'],'weekdays_off':[],'dates_off':[],'courses':[{'course':'Finance','end':end,'decks':['d1']}]},'calendar_events':[]}
    at,calls=setup(monkeypatch,[existing])
    button(at,'Edit').click().run()
    button(at,'Sa').click().run()
    button(at,'Su').click().run()
    button(at,'Save study plan').click().run()
    saved=next(value for action,value in calls if action=='save')
    assert saved['id']=='plan-1' and saved['plan']['weekdays_off']==[5,6]
    assert not at.exception


def test_days_off_and_rejected_plan_cannot_be_saved(monkeypatch):
    at,calls=setup(monkeypatch)
    button(at,'Create study plan').click().run()
    widget(at.text_input,'Plan name').set_value('Short').run()
    widget(at.multiselect,'Courses').set_value(['Finance']).run()
    widget(at.multiselect,'Decks to study').set_value(['d1']).run()
    widget(at.date_input,'Finish by (exam or target date)').set_value(date.today()).run()
    assert not button(at,'Save study plan').disabled
    widget(at.date_input,'Single day without studying').set_value(date.today()).run()
    button(at,'Add day off').click().run()
    assert widget(at.multiselect,'Days off').value==[date.today().isoformat()]
    assert button(at,'Save study plan').disabled and any('no study day left' in i.value for i in at.info)
    widget(at.multiselect,'Days off').set_value([]).run()
    assert not button(at,'Save study plan').disabled
    assert any('**20 questions per day**' in m.value and 'on 3 study days' in m.value for m in at.markdown) is False  # one day only: all 60 answers today
    assert any('**60 questions per day**' in m.value and 'on 1 study day.' in m.value and 'You will be done on your target date' in m.value for m in at.markdown)
    widget(at.date_input,'Finish by (exam or target date)').set_value(date.today()+timedelta(days=9)).run()
    assert widget(at.date_input,'Start studying on').value==date.today()
    widget(at.date_input,'Start studying on').set_value(date.today()+timedelta(days=5)).run()
    assert any('**20 questions per day**' in m.value and ' from ' in m.value and '2 days before your target date' in m.value for m in at.markdown)
    assert not any(a=='save' for a,_ in calls) and not at.exception


def google_plan():
    end=(date.today()+timedelta(days=9)).isoformat()
    return {'id':'plan-1','plan':{'name':'Winter exams','target':2,'sessions':1,'times':['09:00'],'weekdays_off':[],'dates_off':[],'courses':[{'course':'Finance','start':None,'end':end,'decks':['d1']}]},'calendar_events':[{'uid':'old','event_id':'g-old'}]}


def test_google_answer_replaces_only_this_plans_entries(monkeypatch):
    import google_calendar as gc
    monkeypatch.setenv('GOOGLE_CLIENT_ID','client-id');monkeypatch.setenv('GOOGLE_CLIENT_SECRET','client-secret')
    seen={}
    monkeypatch.setattr(gc,'exchange_code',lambda http,cid,secret,redirect,code:seen.update(code=code,redirect=redirect) or 'token')
    monkeypatch.setattr(gc,'remove_events',lambda http,token,recorded:seen.update(removed=list(recorded)) or [])
    monkeypatch.setattr(gc,'add_events',lambda http,token,events:([{'uid':e['uid'],'event_id':'g'+str(i)} for i,e in enumerate(events)],0))
    at,calls=setup(monkeypatch,[google_plan()])
    assert not any(b.label=='Update Google Calendar' for b in at.get('link_button'))
    button(at,'Edit').click().run()
    notice=next(item for item in at.get('popover') if item.proto.popover.label=='Update Google Calendar')
    assert any('registered Google test accounts' in item.value for item in at.caption)
    assert any('registered Google test accounts' in item.value for item in notice.markdown)
    assert any(b.label=='Continue with a registered test account' for b in notice.get('link_button'))
    assert any(b.label=='Calendar file' for b in at.get('download_button'))
    assert not any(a=='events' for a,_ in calls)
    at.query_params['state']=gc.sign_state('client-secret','sync','plan-1','a');at.query_params['code']='one-time-code';at.run()
    assert seen['code']=='one-time-code' and seen['redirect']=='http://localhost:8501' and seen['removed']==[{'uid':'old','event_id':'g-old'}]
    recorded=next(v for a,v in calls if a=='events')
    assert recorded['id']=='plan-1' and len(recorded['events'])==3 and recorded['events'][0]['event_id']=='g0'
    assert any('now has 3 entries' in s.value for s in at.success)
    assert 'code' not in at.query_params and 'state' not in at.query_params
    assert not at.exception


def test_refused_or_foreign_google_answer_changes_nothing(monkeypatch):
    import google_calendar as gc
    monkeypatch.setenv('GOOGLE_CLIENT_ID','client-id');monkeypatch.setenv('GOOGLE_CLIENT_SECRET','client-secret')
    def forbidden(*a,**k):raise AssertionError('Google must not be contacted')
    for name in ('exchange_code','remove_events','add_events'):monkeypatch.setattr(gc,name,forbidden)
    at,calls=setup(monkeypatch,[google_plan()])
    at.query_params['state']=gc.sign_state('client-secret','sync','plan-1','a');at.query_params['error']='access_denied';at.run()
    assert any('not changed' in w.value for w in at.warning)
    at.query_params['state']=gc.sign_state('client-secret','sync','plan-1','someone-else');at.query_params['code']='code';at.run()
    assert any('no longer valid' in e.value for e in at.error)
    assert not any(a=='events' for a,_ in calls) and not at.exception


def test_todays_sessions_start_study_mode_and_stay_fixed_for_the_day(monkeypatch):
    plan=google_plan();plan['calendar_events']=[];plan['plan'].update(sessions=2,times=['09:00','19:00'])
    at,calls=setup(monkeypatch,[plan],levels=(None,)*150)  # 300 answers over 10 days: 30 today, 15 per session
    day=next(v for a,v in calls if a=='day')
    assert day['plan']['day']=={'date':date.today().isoformat(),'planned':{'Finance':30},'open':{'Finance':300}}
    assert button(at,'Start morning session · Finance · 15 questions') and button(at,'Start evening session · Finance · 15 questions')
    at.run()
    assert sum(1 for a,_ in calls if a=='day')==1
    monkeypatch.setattr('study_plan.session_overdue',lambda time,now:time=='09:00')  # the morning is over
    at.run()
    assert button(at,'Catch up on morning session · Finance · 15 questions') and button(at,'Start evening session · Finance · 15 questions')
    assert not any(b.label.startswith('Start morning') for b in at.button)
    button(at,'Start evening session · Finance · 15 questions').click().run()
    started=next(v for a,v in calls if a=='study:start')
    assert {k:started[k] for k in ('deck_id','shared','mode','count','levels','chapters')}=={'deck_id':'d1','shared':False,'mode':'solo','count':15,'levels':['new','0','1'],'chapters':[]}
    assert at.session_state['main_page']=='Play' and at.session_state['study_session']=='session-1'
    assert not at.exception


def test_finished_sessions_are_marked_done_and_plan_is_deleted_only_after_confirmation(monkeypatch):
    plan=google_plan();plan['calendar_events']=[];plan['plan'].update(sessions=2,times=['09:00','19:00'])
    plan['plan']['day']={'date':date.today().isoformat(),'planned':{'Finance':30},'open':{'Finance':300}}
    other=deepcopy(plan);other['id']='plan-2';other['plan']['name']='Second plan'
    at,calls=setup(monkeypatch,[plan,other],levels=(1,)*15+(None,)*135)  # 15 answers earned since the day began
    assert any('Morning session (09:00) is done' in c.value for c in at.caption)
    assert sum(1 for b in at.button if b.label=='Start evening session · Finance · 15 questions')==2
    assert not any('morning' in b.label for b in at.button) and not any(a=='day' for a,_ in calls)
    next(b for b in at.button if b.label=='Edit').click().run()
    button(at,'Delete study plan').click().run()
    assert not any(a=='delete' for a,_ in calls) and any('Winter exams' in w.value for w in at.warning)
    button(at,'Keep plan').click().run()
    assert not any(a=='delete' for a,_ in calls)
    button(at,'Delete study plan').click().run();button(at,'Confirm deletion').click().run()
    assert [v for a,v in calls if a=='delete']==[{'id':'plan-1'}]
    assert not at.exception


def test_plan_to_dos_appear_above_new_solo_session_in_study_mode(monkeypatch):
    plan=google_plan();plan['calendar_events']=[];plan['plan'].update(sessions=2,times=['09:00','19:00'])
    at,calls=setup(monkeypatch,[plan],levels=(None,)*150)
    button(at,'Play').click().run();button(at,'Study Mode').click().run();button(at,'Study alone').click().run()
    labels=[b.label for b in at.button]
    assert 'Start morning session · Finance · 15 questions' in labels and 'Start studying' in labels
    assert labels.index('Start morning session · Finance · 15 questions')<labels.index('Start studying')
    assert any(s.value=='Create a new study session' for s in at.subheader)
    button(at,'Start morning session · Finance · 15 questions').click().run()
    assert any(a=='study:start' for a,_ in calls) and at.session_state['study_session']=='session-1'
    assert not at.exception


def test_google_callback_updates_existing_session_without_deleting_it(monkeypatch):
    import google_calendar as gc
    import study_plan as rules
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-client')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'test-secret')
    plan = google_plan()
    stored_plan = {**plan['plan'], 'id': plan['id']}
    first = rules.plan_sessions(stored_plan, {'Finance': [None] * 30}, date.today())[0]
    uid = rules.session_uid(stored_plan, first)
    plan['calendar_events'].append({'uid': uid, 'event_id': 'legacy-id'})
    monkeypatch.setattr(gc, 'exchange_code', lambda *args: 'token')
    removed, updated = [], []
    monkeypatch.setattr(gc, 'remove_events', lambda http, token, rows: removed.extend(rows) or [])

    def sync(http, token, events):
        updated.extend(events)
        return [{'uid': e['uid'], 'event_id': e.get('event_id', 'new-id')} for e in events], 0

    monkeypatch.setattr(gc, 'add_events', sync)
    at, calls = setup(monkeypatch, [plan])
    at.query_params['state'] = gc.sign_state('test-secret', 'sync', plan['id'], 'a')
    at.query_params['code'] = 'test-code'
    at.run()
    assert not at.exception
    assert removed == [{'uid': 'old', 'event_id': 'g-old'}]
    assert any(e['uid'] == uid and e.get('event_id') == 'legacy-id' for e in updated)
    assert {'uid': uid, 'event_id': 'legacy-id'} in next(v['events'] for a, v in calls if a == 'events')
