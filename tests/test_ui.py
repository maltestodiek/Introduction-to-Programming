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
    p.rpc.assert_not_called()

def test_profile_save_valid_input():
    at,p=signed_in()
    at.multiselect[0].set_value(["Corporate Finance"])
    at.multiselect[1].set_value(["English"])
    next(b for b in at.button if b.label=="Save profile").click().run()
    assert not at.exception
    p.rpc.assert_called_once()
    assert p.rpc.call_args.args[1]["p_courses"]==["Corporate Finance"]

def test_signout_clears_session():
    at,p=signed_in()
    next(b for b in at.button if b.label=="Sign out").click().run()
    assert not at.exception
    assert "Your next study win" in at.title[0].value
    assert at.session_state["auth"].user is None


def test_university_search_populates_choices_and_retains_username():
    from unittest.mock import patch
    at,p=signed_in()
    record={"label":"University of Oxford — United Kingdom","id":"https://ror.org/052gg0110"}
    at.text_input(key="profile_username").set_value("student_kept")
    next(w for w in at.text_input if w.label=="Search universities").set_value("Oxford")
    with patch("universities.search_universities",return_value=[record]) as search:
        next(b for b in at.button if b.label=="Search").click().run()
    search.assert_called_once_with("Oxford")
    assert any(b.label==record["label"] for b in at.button)
    next(b for b in at.button if b.label==record["label"]).click().run()
    assert at.session_state["chosen_university"]==record["label"]
    assert at.text_input(key="profile_username").value=="student_kept"
    assert not at.exception


def test_forgot_password_ui_invalid_email_does_not_send():
    at=AppTest.from_file(str(APP),default_timeout=15).run()
    next(w for w in at.text_input if w.label=="Account email").set_value("bad")
    next(b for b in at.button if b.label=="Send reset link").click().run()
    assert any("valid email" in e.value for e in at.error)
    assert not at.exception
