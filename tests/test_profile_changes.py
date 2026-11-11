from unittest.mock import Mock
from pathlib import Path
from streamlit.testing.v1 import AppTest
from logic import DEFAULT_AVATAR, OPTIONS, render_avatar, validate_profile
from auth import AuthService

def test_signup_error_keeps_inputs_and_shows_username_guidance():
    p=Mock()
    at=AppTest.from_file(str(Path(__file__).parents[1]/"app.py"),default_timeout=15)
    at.session_state["auth"]=AuthService(p)
    at.session_state["account_mode"]="Create account"
    at.run()
    values=["bad name","student@example.test","test-password-123","test-password-123"]
    for field,value in zip(at.text_input,values):field.set_value(value)
    at.button[0].click().run()
    assert [field.value for field in at.text_input]==values
    assert "underscores" in at.error[0].value
    assert any("No spaces" in c.value for c in at.caption)
    p.auth.sign_up.assert_not_called()

def test_ten_distinct_hairstyles_and_ten_accessories():
    assert len(OPTIONS["hair"])==10
    assert len(OPTIONS["accessory"])==11  # Ten accessories plus None.
    for field in ["hair","accessory"]:
        images=[render_avatar(dict(DEFAULT_AVATAR,**{field:value})) for value in OPTIONS[field]]
        assert len(set(images))==len(images)

def test_playful_skin_colors_and_custom_study_information():
    for color in ["Blue","Green","Purple","Pink"]:
        assert color in OPTIONS["skin"]
        assert render_avatar(dict(DEFAULT_AVATAR,skin=color))
    result=validate_profile("student","  Example   University ",["New Course","new course"],["English"],
                            DEFAULT_AVATAR,degree="Master's",area="Finance")
    assert result["university"]=="Example University"
    assert len(result["courses"])==1
    assert result["degree"]=="Master's"
    assert result["area"]=="Finance"


def test_skin_color_labels_are_neutral_and_preserve_saved_values():
    from avatar_picker import SKIN_LABELS
    assert SKIN_LABELS=={"Light":"Light","Medium":"Tanned","Deep":"Coloured"}
    assert all(key in OPTIONS["skin"] for key in SKIN_LABELS)
    for value in SKIN_LABELS:
        assert render_avatar(dict(DEFAULT_AVATAR,skin=value))
