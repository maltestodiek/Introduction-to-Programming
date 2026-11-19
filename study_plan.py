"""Study plan rules: study days, workload in level steps, progress, sessions and calendar text."""
from datetime import date,datetime,timedelta
from math import ceil

DEFAULT_TIMES=['09:00','14:00','19:00']
SECONDS_PER_STEP=15
MINIMUM_MINUTES=15
MINIMUM_PER_DAY=20


def _day(value):
    return value if isinstance(value,date) and not isinstance(value,datetime) else date.fromisoformat(str(value))


def study_days(start,end,weekdays_off,dates_off):
    """Days from start to end (both included) that are neither an excluded weekday nor an excluded date."""
    start,end=_day(start),_day(end);off={_day(d) for d in dates_off};weekdays=set(weekdays_off)
    return [start+timedelta(days=i) for i in range((end-start).days+1) if (start+timedelta(days=i)).weekday() not in weekdays and start+timedelta(days=i) not in off]


def remaining_steps(levels,target):
    """One step is one correct answer: a new or level-0 question needs `target` steps."""
    return sum(max(target-(level or 0),0) for level in levels)


def plan_progress(levels,target):
    """Share of level steps already reached, counting partial levels and capping at the target."""
    levels=list(levels)
    return sum(min(level or 0,target) for level in levels)/(len(levels)*target) if levels else 0.0


def daily_steps(steps,days,minimum=MINIMUM_PER_DAY):
    """Steps for one study day: an even share of what is left, but at least `minimum` (or everything, if less is left)."""
    return min(steps,max(ceil(steps/days) if days else steps,minimum))


def workload(levels,target,days,sessions,minimum=MINIMUM_PER_DAY):
    """`needed` is the number of study days the plan really takes; it can be fewer than the `days` available."""
    steps=remaining_steps(levels,target);per_day=daily_steps(steps,days,minimum)
    return {'steps':steps,'per_day':per_day,'per_session':ceil(per_day/sessions),'days':days,'needed':ceil(steps/per_day) if per_day else 0}


def course_days(plan,item,today):
    """Study days of one course: from today, or from its later start date, until its end date."""
    start=max(today,_day(item['start'])) if item.get('start') else today
    return study_days(start,item['end'],plan['weekdays_off'],plan['dates_off'])


def _time(value):
    try:parsed=datetime.strptime(str(value),'%H:%M')
    except ValueError:raise ValueError('Enter each session time as HH:MM, for example 09:00.') from None
    return parsed.strftime('%H:%M')


def validate_plan(plan,profile_courses,decks_by_course,today):
    """Return a clean plan or raise ValueError naming the problem. Nothing is stored by this function."""
    name=str(plan.get('name') or '').strip()
    if not name or len(name)>60:raise ValueError('Give the plan a name of at most 60 characters.')
    target=plan.get('target')
    if target not in (1,2,3):raise ValueError('Choose a target level of 1, 2 or 3.')
    sessions=plan.get('sessions')
    if sessions not in (1,2,3):raise ValueError('Choose 1, 2 or 3 sessions per day.')
    times=[_time(t) for t in (plan.get('times') or DEFAULT_TIMES[:sessions])]
    if len(times)!=sessions:raise ValueError('Set one start time for each of the sessions.')
    if times!=sorted(set(times)):raise ValueError('Put the session times in order, each one later than the one before.')
    weekdays_off=sorted({int(d) for d in plan.get('weekdays_off') or []})
    if any(d not in range(7) for d in weekdays_off):raise ValueError('Choose weekdays from Monday to Sunday.')
    dates_off=sorted({_day(d).isoformat() for d in plan.get('dates_off') or []})
    courses=[];seen=set()
    if not plan.get('courses'):raise ValueError('Add at least one course to the plan.')
    for item in plan['courses']:
        course=item.get('course')
        if course not in profile_courses:raise ValueError('Only courses from your profile can be added.')
        if course in seen:raise ValueError('Add each course only once.')
        seen.add(course)
        allowed={d['id'] for d in decks_by_course.get(course,[])};decks=list(dict.fromkeys(item.get('decks') or []))
        if not decks or any(d not in allowed for d in decks):raise ValueError(f'Choose at least one deck you can study for {course}.')
        try:end=_day(item.get('end'))
        except (TypeError,ValueError):raise ValueError(f'Choose an end date for {course}.') from None
        if end<today:raise ValueError(f'The end date for {course} is in the past.')
        start=None
        if item.get('start'):
            try:start=_day(item['start'])
            except (TypeError,ValueError):raise ValueError(f'Choose a start date for {course}.') from None
            if start>end:raise ValueError(f'The start date for {course} is after its end date.')
        if not study_days(max(today,start) if start else today,end,weekdays_off,dates_off):raise ValueError(f'There is no study day left before the end date for {course}.')
        courses.append({'course':course,'start':start.isoformat() if start else None,'end':end.isoformat(),'decks':decks})
    clean={'name':name,'target':target,'sessions':sessions,'times':times,'weekdays_off':weekdays_off,'dates_off':dates_off,'courses':courses}
    if plan.get('id'):clean['id']=plan['id']
    return clean


def _spread(total,parts):
    """Split `total` into `parts` whole numbers, larger shares first."""
    return [total//parts+(1 if i<total%parts else 0) for i in range(parts)]


def plan_schedule(plan,levels_by_course,today,minimum=MINIMUM_PER_DAY):
    """Steps per study day and course: {date:{course:steps}}.

    Every course gets an even share of its remaining steps on each of its study days. The minimum applies to the
    whole plan: a day below it is topped up with later steps, taken first from the course that ends soonest.
    """
    state=[{'course':item['course'],'days':course_days(plan,item,today),'left':remaining_steps(levels_by_course.get(item['course'],[]),plan['target'])} for item in sorted(plan['courses'],key=lambda c:c['end'])]
    schedule={}
    for day in sorted({d for course in state for d in course['days']}):
        active=[c for c in state if day in c['days'] and c['left']>0]
        share={c['course']:ceil(c['left']/sum(1 for d in c['days'] if d>=day)) for c in active}
        missing=minimum-sum(share.values())
        for c in active:
            extra=max(0,min(missing,c['left']-share[c['course']]));share[c['course']]+=extra;missing-=extra
        for c in active:c['left']-=share[c['course']]
        if share:schedule[day]=share
    return schedule


def course_outlook(schedule,course):
    """When a course is studied: its first and last planned day, the number of study days and the first day's steps."""
    days=[day for day in sorted(schedule) if schedule[day].get(course)]
    return {'first':days[0],'finish':days[-1],'days':len(days),'per_day':schedule[days[0]][course]} if days else None


def plan_sessions(plan,levels_by_course,today):
    """Planned sessions from today on: [{'date','time','steps','courses':{course:steps}}], ordered by date and time."""
    slots={}
    for day,share in plan_schedule(plan,levels_by_course,today).items():
        for course,day_steps in share.items():
            for time,steps in zip(plan['times'],_spread(day_steps,plan['sessions'])):
                if steps:
                    slot=slots.setdefault((day,time),{'date':day,'time':time,'steps':0,'courses':{}})
                    slot['steps']+=steps;slot['courses'][course]=steps
    return [slots[key] for key in sorted(slots)]


def session_minutes(steps):
    return max(MINIMUM_MINUTES,ceil(steps*SECONDS_PER_STEP/60))


def session_title(plan,session):
    return f"UniArena: {plan['name']} ({session['steps']} questions)"


def session_details(session):
    return ', '.join(f'{course}: {steps}' for course,steps in session['courses'].items())


def session_uid(plan,session):
    return f"{plan.get('id','plan')}-{session['date']:%Y%m%d}-{session['time'].replace(':','')}@studyduel"


def _ics_text(value):
    return str(value).replace('\\','\\\\').replace(';','\\;').replace(',','\\,').replace('\n','\\n')


def plan_ics(plan,sessions):
    """Calendar file with local (floating) times so sessions appear at the chosen clock time."""
    lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//UniArena//Study plan//EN','CALSCALE:GREGORIAN']
    for session in sessions:
        start=datetime.combine(session['date'],datetime.strptime(session['time'],'%H:%M').time());end=start+timedelta(minutes=session_minutes(session['steps']))
        lines+=['BEGIN:VEVENT','UID:'+session_uid(plan,session),f'DTSTAMP:{start:%Y%m%dT%H%M%S}',f'DTSTART:{start:%Y%m%dT%H%M%S}',f'DTEND:{end:%Y%m%dT%H%M%S}',
                'SUMMARY:'+_ics_text(session_title(plan,session)),'DESCRIPTION:'+_ics_text(session_details(session)),'END:VEVENT']
    lines.append('END:VCALENDAR')
    return '\r\n'.join(lines)+'\r\n'


def day_snapshot(plan,levels_by_course,today):
    """What the plan asks for today, fixed when the day is first opened: planned steps and the steps open at that moment."""
    planned=plan_schedule(plan,levels_by_course,today).get(today,{})
    return {'date':today.isoformat(),'planned':planned,'open':{course:remaining_steps(levels_by_course.get(course,[]),plan['target']) for course in planned}}


def session_name(time):
    hour=int(time[:2])
    return 'Morning' if hour<12 else 'Afternoon' if hour<17 else 'Evening'


def session_overdue(time,now):
    """True once the part of the day a session belongs to is over: mornings end at 12:00, afternoons at 17:00."""
    hour=int(time[:2])
    return now.hour>=12 if hour<12 else now.hour>=17 if hour<17 else False


def today_sessions(plan,levels_by_course,today):
    """Today's sessions and what is still open in each: [{'time','name','planned','open','courses':{course:open steps}}].

    The day's amount stays fixed until the day is over, so a session can be done at any time of the day, also late
    in the evening. Answers given today fill the sessions in order. What is still open tomorrow is spread again.
    """
    day=plan.get('day') if (plan.get('day') or {}).get('date')==today.isoformat() else day_snapshot(plan,levels_by_course,today)
    sessions=[{'time':time,'name':session_name(time),'planned':0,'open':0,'courses':{}} for time in plan['times']]
    for course,planned in day['planned'].items():
        left=remaining_steps(levels_by_course.get(course,[]),plan['target']);done=max(day['open'].get(course,left)-left,0)
        for session,steps in zip(sessions,_spread(planned,plan['sessions'])):
            finished=min(done,steps);done-=finished;still=min(steps-finished,left);left-=still
            session['planned']+=steps;session['open']+=still
            if still:session['courses'][course]=still
    return [session for session in sessions if session['planned']]


def plan_checklist(plan,today):
    """What a draft plan still needs before it can be saved, as (label, done) pairs for the editor."""
    courses=plan.get('courses') or []
    def future(value):
        try:return date.fromisoformat(str(value))>=today
        except (TypeError,ValueError):return False
    return [
        ('Name the plan',bool((plan.get('name') or '').strip())),
        ('Add at least one course',bool(courses)),
        ('Choose decks for every course',bool(courses) and all(item.get('decks') for item in courses)),
        ('Set an exam date for every course',bool(courses) and all(future(item.get('end')) for item in courses)),
    ]
