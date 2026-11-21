import pytest
from unittest.mock import Mock

from course_catalog import courses_at_university
from db import ProfileRepository
from test_storage import payload


def test_course_selector_uses_only_the_chosen_university():
    profile = dict(university="North", courses=["Finance", "Law"],
                   course_history={"South": ["Finance", "Tax"]})
    assert courses_at_university(profile, "North") == ["Finance", "Law"]
    assert courses_at_university(profile, "South") == ["Finance", "Tax"]
    assert courses_at_university(profile, "Third") == []


def test_old_profile_can_switch_without_registering_a_new_course():
    data = dict(payload(), university="South", courses=[])
    profile = dict(university="North", courses=["Law"], course_history={})
    client = Mock()
    ProfileRepository(client, "owner").save(data, "Avatar", None, None, previous=profile)
    name, args = client.rpc.call_args.args
    assert name == "save_profile_v4"
    assert args["p_expected_university"] == "North"
    assert args["p_courses"] == []


def test_switch_before_migration_explains_why_and_does_not_write():
    data = dict(payload(), university="South")
    client = Mock()
    with pytest.raises(ValueError, match="database update"):
        ProfileRepository(client, "owner").save(data, "Avatar", None, None,
                                                previous=dict(university="North", courses=["Law"]))
    client.rpc.assert_not_called()


def test_profile_explains_matching_for_a_former_university(monkeypatch):
    from test_profile_summary import courses_profile
    at, _ = courses_profile(monkeypatch)
    profile = ProfileRepository(None, None).load()
    profile["course_history"] = {"North": ["Law"]}
    at.session_state["profile_changed"] = True
    at.run()
    assert not at.exception
    captions = [item.value for item in at.caption]
    rows = [item.value for item in at.markdown]
    assert ":material/school: Private Equity (Example University)" in rows
    assert ":material/school: Law (North)" in rows
    assert any("Switch back" in value for value in captions)


def test_switching_in_editor_restores_only_the_selected_campus(monkeypatch):
    from test_profile_summary import courses_profile, saves
    at, client = courses_profile(monkeypatch)
    profile = ProfileRepository(None, None).load()
    profile["course_history"] = {"North": ["Law"]}
    next(b for b in at.button if b.label == "Edit profile").click().run()
    def editor():
        return next(w for w in at.multiselect if w.label == "Your courses")
    assert list(editor().value) == ["Private Equity"]
    for index, (university, expected) in enumerate([("North", ["Law"]), ("South", [])], start=1):
        at.session_state["chosen_university"] = university
        at.session_state["university_pick"] = index
        at.run()
        assert not at.exception
        assert list(editor().value) == expected
    next(b for b in at.button if b.label == "Save profile").click().run()
    assert not at.exception
    assert saves(client)[-1]["p_courses"] == []
    assert saves(client)[-1]["p_university"] == "South"
