"""The app is called CampusDuel everywhere a user can see it."""
from pathlib import Path

from test_deck_ui import deck_app

ROOT=Path(__file__).parents[1]
# Technical identifiers that keep their value so existing sessions, calendar entries and links keep working.
KEPT=('studyduel-nova','studyduel-example','studyduel.resume.v1','@studyduel','Library/Caches/StudyDuel')


def app_sources():
    return [p for p in ROOT.iterdir() if p.suffix in ('.py','.sh')]+list((ROOT/'assets').glob('*.css'))


def test_no_user_facing_text_uses_the_old_name():
    for path in app_sources():
        text=path.read_text()
        for kept in KEPT:text=text.replace(kept,'')
        assert 'studyduel' not in text.lower().replace(' ',''), path.name


def test_header_wordmark_and_page_title_say_campusduel(monkeypatch):
    at=deck_app(monkeypatch)
    assert next(b for b in at.button if b.key=='open_home').label=='Campus**Duel**'
    assert 'page_title="CampusDuel"' in (ROOT/'app.py').read_text()
    assert not at.exception


def test_welcome_screen_says_campusduel():
    from streamlit.testing.v1 import AppTest
    at=AppTest.from_file(str(ROOT/'app.py')).run()
    bodies=' '.join(element.proto.body for element in at.get('html'))
    assert 'Welcome to CampusDuel' in bodies and 'Campus<span>Duel</span>' in bodies
    assert not at.exception
