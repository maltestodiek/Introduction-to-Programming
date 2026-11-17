import base64
import re
from pathlib import Path

from appearance import PROFILE_BUTTON_AVATAR_SIZE, profile_button_avatar_css
from logic import DEFAULT_AVATAR, render_avatar
from test_deck_ui import button, deck_app

NAVIGATION_CSS=(Path(__file__).parents[1]/'assets'/'navigation.css').read_text()


def html_bodies(at):
    return [element.proto.body for element in at.get('html')]


def test_profile_button_css_paints_the_given_picture():
    css=profile_button_avatar_css(b'picture-bytes')
    assert css.startswith('.st-key-open_profile button::before{')
    assert 'data:image/png;base64,'+base64.b64encode(b'picture-bytes').decode() in css


def test_profile_button_picture_replaces_the_mask_icon_and_stays_small():
    rules=re.findall(r'\.st-key-open_profile button::before\{([^}]*)\}',NAVIGATION_CSS)
    assert rules, 'the Profile button needs its own artwork rule'
    declarations=';'.join(rules)
    assert 'mask-image:none' in declarations and '-webkit-mask-image:none' in declarations
    assert 'data:image/svg+xml' not in declarations
    assert 'border-radius:50%' in declarations
    assert f'width:{PROFILE_BUTTON_AVATAR_SIZE}px' in declarations
    assert f'height:{PROFILE_BUTTON_AVATAR_SIZE}px' in declarations
    assert PROFILE_BUTTON_AVATAR_SIZE<=30


def test_header_shows_the_picture_inside_the_profile_button_only(monkeypatch):
    at=deck_app(monkeypatch)
    bodies=html_bodies(at)
    default_picture=base64.b64encode(render_avatar(DEFAULT_AVATAR)).decode()
    assert any(profile_button_avatar_css(render_avatar(DEFAULT_AVATAR)) in body for body in bodies)
    assert not any('alt="Profile picture"' in body and default_picture in body for body in bodies)
    assert not at.exception


def test_profile_button_still_opens_the_profile_page(monkeypatch):
    at=deck_app(monkeypatch)
    button(at,'Profile').click().run()
    assert button(at,'Edit profile')
    assert not at.exception
