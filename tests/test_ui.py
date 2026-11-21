from pathlib import Path
from unittest.mock import Mock
from types import SimpleNamespace as Obj
from streamlit.testing.v1 import AppTest
from auth import AuthService

APP=Path(__file__).parents[1]/"app.py"

def signed_in():
    p=Mock()
    p.auth.get_user.return_value=Obj(user=Obj(id="a",user_metadata={"username":"student_a"}))
    p.table.return_value.select.return_value.eq.return_value.execute.return_value=Obj(data=[])
    service=AuthService(p);service.user=p.auth.get_user.return_value.user
    at=AppTest.from_file(str(APP),default_timeout=15)
    at.session_state["auth"]=service
    at.session_state["chosen_university"]="Example University"
    at.run()
    return at,p

def test_signin_screen_and_invalid_email():
    at=AppTest.from_file(str(APP),default_timeout=15).run()
    next(b for b in at.button if b.label=="Start").click().run()
    assert not at.exception
    at.text_input[0].set_value("bad")
    at.text_input[1].set_value("password123")
    at.button[0].click().run()
    assert "valid email" in at.error[0].value
    assert not at.exception

def test_profile_requires_courses_and_languages():
    at,p=signed_in()
    assert not at.exception
    next(b for b in at.button if b.label=="Save profile").click().run()
    assert "course" in at.error[0].value
    # Loading the shared course list is a read; no profile may be saved.
    assert not [c for c in p.rpc.call_args_list if c.args[0].startswith('save_profile')]

def test_profile_save_valid_input():
    at,p=signed_in()
    at.multiselect[0].set_value(["Corporate Finance"])
    at.multiselect[1].set_value(["English"])
    next(b for b in at.button if b.label=="Save profile").click().run()
    assert not at.exception
    saves=[c for c in p.rpc.call_args_list if c.args[0].startswith('save_profile')]  # the shared course list is read separately
    assert len(saves)==1
    assert saves[0].args[1]["p_courses"]==["Corporate Finance"]

def test_signout_clears_session(monkeypatch):
    from test_play_landing import PROFILE

    monkeypatch.setattr('db.ProfileRepository.load', lambda self: PROFILE.copy())
    at, client = signed_in()
    next(b for b in at.button if b.label == 'Profile').click().run()
    at.button(key='profile_sign_out').click().run()

    client.auth.sign_out.assert_called_once()
    assert at.session_state['auth'].user is None
    assert any(b.label == 'Sign in' for b in at.button)
    assert 'Your next study win' in at.title[0].value
    assert not at.exception


def profile_form_with_picker(pick,known=()):
    """The profile form with the browser type-ahead replaced by `pick(known, current, key)`."""
    from unittest.mock import patch
    at,p=signed_in()
    p.table.return_value.select.return_value.execute.return_value=Obj(data=[{"university":n} for n in known])
    if "known_universities" in at.session_state:del at.session_state["known_universities"]
    picker=Mock(side_effect=pick)
    return at,p,picker,patch("university_picker.university_picker",picker)


def test_university_field_gets_the_universities_already_in_use_and_the_current_choice():
    at,p,picker,patched=profile_form_with_picker(lambda known,current,key:(current,"saved"),
        ["Bocconi University — Italy","bocconi university — italy","NOVA School of Business and Economics — Portugal"," "])
    with patched:at.run()
    known,current=picker.call_args.args[:2]
    assert known==["Bocconi University — Italy","NOVA School of Business and Economics — Portugal"]
    assert current=="Example University"
    assert not at.exception


def test_a_university_picked_from_the_suggestions_is_final_and_retains_username():
    from unittest.mock import patch
    label="University of Oxford — United Kingdom"
    at,p,picker,patched=profile_form_with_picker(lambda known,current,key:(label,"directory"))
    at.text_input(key="profile_username").set_value("student_kept")
    with patched,patch("universities.search_universities") as search:
        at.run()
        search.assert_not_called()  # the browser already searched the directory
    assert at.session_state["chosen_university"]==label
    assert at.text_input(key="profile_username").value=="student_kept"
    assert not any(str(b.key).startswith("uni_") for b in at.button)
    assert not at.exception


def test_a_name_that_was_only_typed_is_looked_up_and_can_take_the_official_name():
    from unittest.mock import patch
    record={"label":"University of Oxford — United Kingdom","id":"https://ror.org/052gg0110"}
    typed=lambda known,current,key:("Oxford","typed") if key.endswith("_0") else (current,"saved")
    at,p,picker,patched=profile_form_with_picker(typed)
    with patched,patch("universities.search_universities",return_value=[record]) as search:
        at.run()
        search.assert_called_once_with("Oxford")
        assert at.session_state["chosen_university"]=="Oxford"  # usable as typed until a match is chosen
        next(b for b in at.button if b.label==record["label"]).click().run()
    assert at.session_state["chosen_university"]==record["label"]
    assert picker.call_args.kwargs["key"].endswith("_1")  # the field is redrawn with the official name
    assert not any(b.label==record["label"] for b in at.button)
    assert not at.exception


def test_typed_university_is_kept_when_the_directory_has_no_match_or_is_down():
    from unittest.mock import patch
    from universities import UniversitySearchError
    at,p,picker,patched=profile_form_with_picker(lambda known,current,key:("Small Town College","typed"))
    with patched,patch("universities.search_universities",return_value=[]):
        at.run()
    assert at.session_state["chosen_university"]=="Small Town College"
    assert any("No match" in i.value for i in at.info)
    at,p,picker,patched=profile_form_with_picker(lambda known,current,key:("Hilltop Academy","typed"))
    with patched,patch("universities.search_universities",side_effect=UniversitySearchError("University search is unavailable right now. You can still type your university below.")):
        at.run()
    assert at.session_state["chosen_university"]=="Hilltop Academy"
    assert any("unavailable" in w.value for w in at.warning)
    assert not at.exception


def test_universities_in_use_cannot_break_the_form_when_unreadable():
    at,p,picker,patched=profile_form_with_picker(lambda known,current,key:(current,"saved"))
    p.table.return_value.select.return_value.execute.side_effect=Exception("offline")
    with patched:at.run()
    assert picker.call_args.args[0]==[]
    assert not at.exception


def test_stored_field_values_are_cleaned_before_use():
    from university_picker import clean_choice
    assert clean_choice({"name":"  Small   Town College ","source":"typed"},"Old")==("Small Town College","typed")
    assert clean_choice({"name":"X"*300,"source":"directory"},"Old")==("X"*160,"directory")
    assert clean_choice({"name":"Bocconi University — Italy","source":"elsewhere"},"Old")==("Bocconi University — Italy","saved")
    for broken in (None,"text",{"name":5},{"name":" "},{"source":"typed"}):
        assert clean_choice(broken,"Old")==("Old","saved")


def test_university_field_searches_the_directory_in_the_browser_with_the_typed_text_only():
    import university_picker
    assert "https://api.ror.org/v2/organizations?" in university_picker.JS and "types:education" in university_picker.JS
    assert 'role="combobox"' in university_picker.HTML and 'role="listbox"' in university_picker.HTML and 'aria-live="polite"' in university_picker.HTML
    for private in ("username","email","token","user_id","session"):
        assert private not in university_picker.JS


def test_forgot_password_ui_invalid_email_does_not_send():
    at=AppTest.from_file(str(APP),default_timeout=15).run()
    next(b for b in at.button if b.label=="Start").click().run()
    next(w for w in at.text_input if w.label=="Account email").set_value("bad")
    next(b for b in at.button if b.label=="Send reset link").click().run()
    assert any("valid email" in e.value for e in at.error)
    assert not at.exception


