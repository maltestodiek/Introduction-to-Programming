from test_deck_ui import deck_app,button

def test_main_tabs_and_profile_button(monkeypatch):
    at=deck_app(monkeypatch)
    for label in ['Decks','Play','Friends','Leaderboard','Study Plan','Profile']:
        assert button(at,label)
    for page in ['Leaderboard','Study Plan']:
        button(at,page).click().run()
        assert at.title[0].value==page
        assert any(i.value=='Coming soon' for i in at.info)
        assert not at.exception
    button(at,'Decks').click().run()
    assert button(at,'+ Create New Deck')
    button(at,'Profile').click().run()
    assert button(at,'Edit profile')
    assert not at.exception
