from pathlib import Path
from types import SimpleNamespace as Obj
from unittest.mock import Mock

from streamlit.testing.v1 import AppTest

from auth import AuthService
from course_catalog import FIELDS_OF_STUDY, course_options, field_options, load_university_courses, match_courses

APP=Path(__file__).parents[1]/'app.py'


def test_field_list_holds_common_degree_subjects_under_everyday_names():
    for field in ('Business Administration','Finance','Economics','Law','Computer Science','Medicine','Mechanical Engineering','Psychology','International Management'):
        assert field in FIELDS_OF_STUDY
    assert len(FIELDS_OF_STUDY)>=150 and len(set(FIELDS_OF_STUDY))==len(FIELDS_OF_STUDY)
    assert FIELDS_OF_STUDY==sorted(FIELDS_OF_STUDY,key=str.lower)
    assert all(len(field)<=120 for field in FIELDS_OF_STUDY)


def test_field_options_keep_a_previously_saved_custom_value():
    assert field_options('')==FIELDS_OF_STUDY
    assert field_options('Law')==FIELDS_OF_STUDY
    assert field_options('Agribusiness')[0]=='Agribusiness' and field_options('Agribusiness')[1:]==FIELDS_OF_STUDY


def test_typed_courses_take_the_listed_spelling_without_duplicates():
    known=['Corporate Finance','Investments']
    assert match_courses(['corporate  finance','Derivatives ',' INVESTMENTS','Corporate Finance','  '],known)==['Corporate Finance','Derivatives','Investments']
    assert match_courses(['derivatives','Derivatives'],known)==['derivatives']
    assert match_courses([],known)==[]


def test_course_options_join_shared_and_own_courses_once():
    assert course_options(['Corporate Finance','Investments'],['investments','Private Equity'])==['Corporate Finance','Investments','Private Equity']


def test_course_list_is_loaded_per_university_and_never_breaks_the_form():
    client=Mock();client.rpc.return_value.execute.return_value.data=['Investments','Corporate Finance']
    assert load_university_courses(client,' Example University ')==['Investments','Corporate Finance']
    client.rpc.assert_called_once_with('university_courses',{'p_university':'Example University'})
    client.rpc.reset_mock();assert load_university_courses(client,' ')==[];client.rpc.assert_not_called()
    client.rpc.return_value.execute.side_effect=Exception('offline')
    assert load_university_courses(client,'Example University')==[]
    client=Mock();client.rpc.return_value.execute.return_value.data={'error':'no'}
    assert load_university_courses(client,'Example University')==[]


def profile_form(shared):
    p=Mock()
    p.auth.get_user.return_value=Obj(user=Obj(id='a',user_metadata={'username':'student_a'}))
    p.table.return_value.select.return_value.eq.return_value.execute.return_value=Obj(data=[])
    def rpc(name,args=None):
        call=Mock();call.execute.return_value.data=shared if name=='university_courses' else None
        return call
    p.rpc.side_effect=rpc
    service=AuthService(p);service.user=p.auth.get_user.return_value.user
    at=AppTest.from_file(str(APP),default_timeout=15)
    at.session_state['auth']=service;at.session_state['chosen_university']='Example University'
    return at.run(),p


def test_profile_form_offers_shared_courses_and_saves_the_listed_spelling():
    at,p=profile_form(['Corporate Finance','Investments'])
    assert not at.exception
    courses=next(w for w in at.multiselect if w.label=='Your courses')
    assert list(courses.options)==['Corporate Finance','Investments']
    assert ('university_courses',{'p_university':'Example University'}) in [c.args for c in p.rpc.call_args_list]
    courses.set_value(['corporate finance','Derivatives'])
    next(w for w in at.multiselect if w.label=='Languages').set_value(['English'])
    next(b for b in at.button if b.label=='Save profile').click().run()
    assert not at.exception
    saved=[c.args[1] for c in p.rpc.call_args_list if c.args[0].startswith('save_profile')]
    assert len(saved)==1 and saved[0]['p_courses']==['Corporate Finance','Derivatives']


def test_profile_form_field_of_study_is_a_list_that_accepts_other_values():
    at,p=profile_form([])
    field=next(w for w in at.selectbox if w.label=='Field of study (optional)')
    assert 'Business Administration' in field.options and field.value is None
    field.set_value('Law')
    next(w for w in at.multiselect if w.label=='Your courses').set_value(['Roman Law'])
    next(w for w in at.multiselect if w.label=='Languages').set_value(['English'])
    next(b for b in at.button if b.label=='Save profile').click().run()
    assert not at.exception
    saved=[c.args[1] for c in p.rpc.call_args_list if c.args[0].startswith('save_profile')]
    assert saved[0]['p_area']=='Law'


def test_a_saved_course_in_another_spelling_is_shown_in_the_listed_spelling(monkeypatch):
    from logic import DEFAULT_AVATAR
    profile={'username':'student_a','university':'Example University','courses':['corporate finance','Private Equity'],'languages':['English'],'avatar':DEFAULT_AVATAR,'image_mode':'Avatar'}
    monkeypatch.setattr('db.ProfileRepository.load',lambda self:profile)
    monkeypatch.setattr('db.FriendsRepository.action',lambda self,action,value='':{'code':'AB23CD45','friends':[],'incoming':[],'sent':[],'invite_expires':None})
    client=Mock();client.auth.get_user.return_value=Obj(user=Obj(id='a'))
    def rpc(name,args=None):
        call=Mock();call.execute.return_value.data=['Corporate Finance','Investments'] if name=='university_courses' else None
        return call
    client.rpc.side_effect=rpc
    auth=AuthService(client);auth.user=client.auth.get_user.return_value.user
    at=AppTest.from_file(str(APP),default_timeout=15)
    at.session_state['auth']=auth;at.session_state['main_page']='Profile';at.session_state['editing']=True
    at.run()
    assert not at.exception
    courses=next(w for w in at.multiselect if w.label=='Your courses')
    assert list(courses.value)==['Corporate Finance','Private Equity']
    assert list(courses.options)==['Corporate Finance','Investments','Private Equity']
