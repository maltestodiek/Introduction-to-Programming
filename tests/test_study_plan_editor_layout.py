from datetime import date, timedelta

from study_plan import plan_checklist
from test_study_plan_ui import button, setup, widget


def test_checklist_names_what_is_still_missing():
    today=date(2026,11,19)
    empty={'name':'','courses':[]}
    assert plan_checklist(empty,today)==[('Name the plan',False),('Add at least one course',False),('Choose decks for every course',False),('Set a target date for every course',False)]
    ready={'name':'Winter exams','courses':[{'course':'Finance','decks':['d1'],'end':'2026-11-28'}]}
    assert all(done for _,done in plan_checklist(ready,today))
    past={'name':'Winter exams','courses':[{'course':'Finance','decks':[],'end':'2026-11-01'}]}
    assert plan_checklist(past,today)[2:]==[('Choose decks for every course',False),('Set a target date for every course',False)]


def test_new_plan_preview_guides_until_the_plan_can_be_saved(monkeypatch):
    at,calls=setup(monkeypatch)
    button(at,'Create study plan').click().run()
    text=' '.join(item.value for item in at.markdown)
    assert 'To save this plan' in text and ':material/radio_button_unchecked: Name the plan' in text
    assert button(at,'Save study plan').disabled
    widget(at.text_input,'Plan name').set_value('Winter exams').run()
    widget(at.multiselect,'Courses').set_value(['Finance']).run()
    assert [item.value for item in at.caption if item.value in ('Course','Decks','Target date')]==['Course','Decks','Target date']
    assert any(item.label=='Start later (optional)' for item in at.expander)
    widget(at.multiselect,'Decks to study').set_value(['d1']).run()
    widget(at.date_input,'Target date').set_value(date.today()+timedelta(days=9)).run()
    assert 'To save this plan' not in ' '.join(item.value for item in at.markdown)
    assert any('Per study day' in item.value for item in at.get('html'))
    assert any(
        'after saving' in item.value.lower()
        and 'download a calendar file' in item.value.lower()
        and 'Google Calendar' in item.value
        and 'registered Google test accounts' in item.value
        for item in at.caption
    )
    assert not any(action in ('save', 'events') for action, _ in calls)
    assert not button(at,'Save study plan').disabled
    assert not at.exception


def test_level_cards_and_compact_week_controls_create_the_plan(monkeypatch):
    at,calls=setup(monkeypatch)
    button(at,'Create study plan').click().run()
    widget(at.text_input,'Plan name').set_value('Winter exams').run()
    widget(at.multiselect,'Courses').set_value(['Finance']).run()
    widget(at.multiselect,'Decks to study').set_value(['d1']).run()
    end=date.today()+timedelta(days=9)
    widget(at.date_input,'Target date').set_value(end).run()
    button(at,'Level 3').click().run()
    button(at,'Su').click().run()
    button(at,'3').click().run()
    assert [w.label for w in at.time_input]==['Session 1 starts at','Session 2 starts at','Session 3 starts at']
    button(at,'Save study plan').click().run()
    saved=next(value for action,value in calls if action=='save')['plan']
    assert (saved['target'],saved['sessions'],saved['weekdays_off'],saved['courses'][0]['end'])==(3,3,[6],end.isoformat())
    assert any(item.value=='Study plan saved: Winter exams' for item in at.subheader)
    assert not at.exception
