from test_deck_ui import deck_app,button

def test_main_tabs_and_profile_button(monkeypatch):
    at=deck_app(monkeypatch)
    for label in ['Decks','Play','Friends','Leaderboard','Study Plan','Profile']:
        assert button(at,label)
    # Leaderboard is no longer a placeholder: see specs/tasks/leaderboard.md and tests/test_leaderboard_ui.py.
    button(at,'Leaderboard').click().run()
    assert at.title[0].value=='Leaderboard'
    assert not any(i.value=='Coming soon' for i in at.info)
    assert not at.exception
    # Study Plan is no longer a placeholder: see specs/tasks/study-plan.md and tests/test_study_plan_ui.py.
    button(at,'Study Plan').click().run()
    assert at.title[0].value=='Study Plan'
    assert not any(i.value=='Coming soon' for i in at.info)
    assert not at.exception
    button(at,'Decks').click().run()
    assert button(at,'+ Create New Deck')
    button(at,'Profile').click().run()
    assert button(at,'Edit profile')
    assert not at.exception
