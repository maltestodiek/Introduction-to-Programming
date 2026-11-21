import re
from pathlib import Path

from test_deck_ui import button, deck_app

NAVIGATION_CSS=(Path(__file__).parents[1]/'assets'/'navigation.css').read_text()
FRIENDS_CSS=(Path(__file__).parents[1]/'assets'/'friends.css').read_text()
APP=(Path(__file__).parents[1]/'app.py').read_text()


def keyed(at,key):
    return next(b for b in at.button if b.key==key)


def test_large_tabs_no_longer_include_friends(monkeypatch):
    at=deck_app(monkeypatch)
    tabs=[b.label for b in at.button if str(b.key).startswith('nav_')]
    assert tabs==['Decks','Play','Leaderboard','Study Plan']
    assert not at.exception


def test_play_shows_a_badge_for_incoming_battle_invitations(monkeypatch):
    monkeypatch.setattr('db.BattleRepository.action',lambda self,action,data=None:{
        'sessions':[],'search':None,'invites':[{'id':'battle-invite','incoming':True}]
    } if action=='list' else {})
    at=deck_app(monkeypatch)
    assert "if label=='Play' and battle_invites:" in APP
    assert keyed(at,'nav_Play')
    assert not at.exception


def test_friends_sits_in_the_separate_sidebar_account_group(monkeypatch):
    at=deck_app(monkeypatch)
    keys=[str(b.key) for b in at.button]
    assert keyed(at,'open_friends').label=='Friends'
    assert keys.index('nav_Decks')<keys.index('open_friends')<keys.index('open_profile')


def test_navigation_uses_a_left_sidebar_with_separate_account_actions():
    assert "with st.container(key='sidebar_navigation'):" in APP
    assert "with st.container(key='top_brand'):" in APP
    assert "['Decks','Play','Leaderboard','Study Plan']" in APP
    assert "with st.container(key='sidebar_main_actions'):" in APP
    assert "with st.container(key='sidebar_account_actions'):" in APP
    assert "chat_navigation(auth.client, page == 'Chats')" in APP


def test_header_friends_button_opens_the_friends_page(monkeypatch):
    monkeypatch.setattr('db.FriendsRepository.action',lambda self,action,value='':{'code':'AB23CD45','friends':[],'incoming':[],'sent':[],'invite_expires':None})
    at=deck_app(monkeypatch)
    keyed(at,'open_friends').click().run()
    assert at.title[0].value=='Friends'
    assert not at.exception


def test_sidebar_account_buttons_share_layout_and_chat_icon_animation():
    assert '.st-key-nav_Friends' not in NAVIGATION_CSS
    shared=re.findall(r':is\((\[class\*="st-key-nav_[^)]*)\) button\{',NAVIGATION_CSS)
    selectors=('.st-key-open_friends', '.st-key-open_chats', '.st-key-open_profile')
    assert shared and all(all(selector in group for selector in selectors) for group in shared)
    assert re.search(r'\.st-key-open_friends button::before\{mask-image:url\("data:image/svg\+xml',NAVIGATION_CSS)
    rows = '.st-key-sidebar_navigation :is(.st-key-sidebar_main_actions,.st-key-sidebar_account_actions) button'
    layout = re.search(re.escape(rows) + r'\{([^}]*)\}', NAVIGATION_CSS).group(1)
    assert 'grid-template-columns:30px minmax(0,1fr);align-items:center' in layout
    assert 'border-left-width:4px' in layout
    assert rows + '::before{justify-self:center}' in NAVIGATION_CSS
    assert rows + '>div{justify-self:stretch;justify-content:center}' in NAVIGATION_CSS
    assert '.st-key-open_chats button:is(:hover,:focus-visible)::before{animation:nav-bounce' in NAVIGATION_CSS
    reduced_motion=NAVIGATION_CSS.split('@media(prefers-reduced-motion:reduce)',1)[1]
    assert '.st-key-open_chats) button::before{animation:none!important}' in reduced_motion


def test_sidebar_has_consistent_vertical_actions_and_reserves_main_content_space():
    assert '.st-key-sidebar_navigation{position:fixed' in NAVIGATION_CSS
    assert '.st-key-sidebar_navigation .stButton{width:100%}' in NAVIGATION_CSS
    assert '.st-key-open_chats){width:100%!important}' in NAVIGATION_CSS
    assert '.st-key-open_chats){width:calc(14rem - 1.3rem)!important}' in NAVIGATION_CSS
    assert 'padding-top:.75rem!important' in NAVIGATION_CSS
    assert 'max-width:940px!important' in NAVIGATION_CSS
    assert 'margin-left:auto!important;margin-right:auto!important' in NAVIGATION_CSS
    assert 'text-align:left!important' in NAVIGATION_CSS
    assert 'justify-content:flex-start' in NAVIGATION_CSS
    assert '.st-key-open_chats) button:focus-visible{outline:' in NAVIGATION_CSS
    assert '.st-key-nav_play_invite_badge .st-key-nav_Play button::after{content:"1"' in NAVIGATION_CSS


def test_friends_styles_do_not_change_the_shared_page_container_or_header():
    assert '.block-container' not in FRIENDS_CSS


def test_invite_card_headings_match_the_friends_section_heading_scale():
    assert 'font-size:1.5rem!important' in FRIENDS_CSS


def test_invite_card_uses_labeled_code_and_link_sections():
    assert 'Share your code or a link' in APP
    assert 'YOUR FRIEND CODE' in APP
    assert 'ADD FRIEND BY CODE' in APP
    assert 'INVITATION LINK' in APP
    assert 'Active until' in APP


def _sidebar_rule():
    return re.search(r'\.st-key-sidebar_navigation\{([^}]*)\}',NAVIGATION_CSS).group(1)


def test_desktop_sidebar_is_a_full_height_bar_along_the_left_edge():
    rule=_sidebar_rule()
    assert 'position:fixed' in rule
    assert 'top:0' in rule and 'left:0' in rule and 'bottom:0' in rule
    assert 'width:14rem' in rule
    assert 'border-radius' not in rule
    assert 'border-right:1px solid' in rule


def test_desktop_offsets_require_a_visible_sidebar():
    main = '.stMain:has(.st-key-sidebar_navigation){padding-left:14rem}'
    header = '.stApp:has(.st-key-sidebar_navigation) .stAppHeader{left:14rem!important'
    assert main in NAVIGATION_CSS and header in NAVIGATION_CSS
    assert '.stMain{padding-left:14rem' not in NAVIGATION_CSS
    assert not re.search(r'(?:^|[{}])\s*\.stAppHeader\{left:14rem', NAVIGATION_CSS)


def test_narrow_screens_keep_the_sidebar_in_normal_document_flow():
    narrow=re.search(r'@media\(max-width:760px\)\{\.st-key-sidebar_navigation\{([^}]*)\}',NAVIGATION_CSS)
    assert narrow and 'position:static' in narrow.group(1) and 'border:none' in narrow.group(1)
    assert '.stMain{padding-left:0' in NAVIGATION_CSS
