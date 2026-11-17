import re
from pathlib import Path

from test_deck_ui import button, deck_app

NAVIGATION_CSS=(Path(__file__).parents[1]/'assets'/'navigation.css').read_text()


def keyed(at,key):
    return next(b for b in at.button if b.key==key)


def test_large_tabs_no_longer_include_friends(monkeypatch):
    at=deck_app(monkeypatch)
    tabs=[b.label for b in at.button if str(b.key).startswith('nav_')]
    assert tabs==['Decks','Play','Leaderboard','Study Plan']
    assert not at.exception


def test_friends_sits_in_the_header_after_profile_and_before_the_tabs(monkeypatch):
    at=deck_app(monkeypatch)
    keys=[str(b.key) for b in at.button]
    assert keyed(at,'open_friends').label=='Friends'
    assert keys.index('open_profile')<keys.index('open_friends')<keys.index('nav_Decks')


def test_header_friends_button_opens_the_friends_page(monkeypatch):
    monkeypatch.setattr('db.FriendsRepository.action',lambda self,action,value='':{'code':'AB23CD45','friends':[],'incoming':[],'sent':[],'invite_expires':None})
    at=deck_app(monkeypatch)
    keyed(at,'open_friends').click().run()
    assert at.title[0].value=='Friends'
    assert not at.exception


def test_friends_button_shares_profile_button_styling_and_keeps_its_icon():
    assert '.st-key-nav_Friends' not in NAVIGATION_CSS
    shared=re.findall(r':is\(([^)]*)\) button\{',NAVIGATION_CSS)
    assert shared and all('.st-key-open_profile' in s and '.st-key-open_friends' in s for s in shared)
    assert re.search(r'\.st-key-open_friends button::before\{mask-image:url\("data:image/svg\+xml',NAVIGATION_CSS)
