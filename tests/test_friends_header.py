import re
from pathlib import Path

from test_deck_ui import button, deck_app

NAVIGATION_CSS=(Path(__file__).parents[1]/'assets'/'navigation.css').read_text()
APP=(Path(__file__).parents[1]/'app.py').read_text()


def keyed(at,key):
    return next(b for b in at.button if b.key==key)


def test_large_tabs_no_longer_include_friends(monkeypatch):
    at=deck_app(monkeypatch)
    tabs=[b.label for b in at.button if str(b.key).startswith('nav_')]
    assert tabs==['Decks','Play','Leaderboard','Study Plan']
    assert not at.exception


def test_friends_sits_in_the_separate_account_header_group(monkeypatch):
    at=deck_app(monkeypatch)
    keys=[str(b.key) for b in at.button]
    assert keyed(at,'open_friends').label=='Friends'
    assert keys.index('nav_Decks')<keys.index('open_friends')<keys.index('open_profile')


def test_header_uses_one_compact_navigation_shell_with_separate_account_actions():
    assert "with st.container(key='top_brand')" in APP
    assert "main_navigation,account_navigation=st.columns([4,1.2],gap='medium'" in APP
    assert "['Decks','Play','Leaderboard','Study Plan']" in APP
    assert "st.columns(4,gap='small')" in APP
    assert "friends_slot,chats_slot,profile_slot=st.columns(3" in APP
    assert "chat_dropdown(auth.client,compact=True)" in APP


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


def test_compact_header_actions_and_navigation_tabs_have_matching_compact_heights():
    assert 'min-height:44px' in NAVIGATION_CSS
    assert 'gap:.35rem!important' in NAVIGATION_CSS
    assert 'gap:.5rem!important' in NAVIGATION_CSS
    assert 'left:50%;top:50%;transform:translate(-50%,-50%)' in NAVIGATION_CSS
