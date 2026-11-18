"""The app is called UniArena everywhere a user can see it."""
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
        squeezed=text.lower().replace(' ','')
        assert 'studyduel' not in squeezed and 'campusduel' not in squeezed, path.name


def test_header_wordmark_and_page_title_say_uniarena(monkeypatch):
    at=deck_app(monkeypatch)
    assert next(b for b in at.button if b.key=='open_home').label=='Uni**Arena**'
    assert 'page_title="UniArena"' in (ROOT/'app.py').read_text()
    assert not at.exception


def test_welcome_screen_says_uniarena():
    from streamlit.testing.v1 import AppTest
    at=AppTest.from_file(str(ROOT/'app.py')).run()
    bodies=' '.join(element.proto.body for element in at.get('html'))
    assert 'Welcome to UniArena' in bodies and 'Uni<span>Arena</span>' in bodies
    assert not at.exception


def test_logo_file_is_transparent_and_uses_both_brand_colours():
    from PIL import Image
    im=Image.open(ROOT/'assets'/'uniarena-icon.png').convert('RGBA')
    assert im.width>im.height  # the mark is wide; app.py pads it to a square for the browser tab
    assert all(im.getpixel(corner)[3]==0 for corner in ((0,0),(im.width-1,0),(0,im.height-1),(im.width-1,im.height-1)))
    small=im.resize((64,64))
    pixels=[small.getpixel((x,y)) for x in range(64) for y in range(64)]  # sampled from a squeezed copy; only colours matter
    indigo=sum(1 for r,g,b,a in pixels if a>200 and b>180 and r<110 and g<110)
    mint=sum(1 for r,g,b,a in pixels if a>200 and g>190 and r<140 and b<200)
    assert indigo>40 and mint>40
    # the two cards rise above the arena: solid indigo and mint in the top third of the mark
    top=[small.getpixel((x,y)) for x in range(64) for y in range(4,22)]
    assert sum(1 for r,g,b,a in top if a>200 and b>180 and r<110 and g<110)>25
    assert sum(1 for r,g,b,a in top if a>200 and g>190 and r<140 and b<200)>25
    # the arena makes the mark wider than the two cards alone, which were taller than wide
    left,top,right,bottom=im.getbbox()
    assert (right-left)>(bottom-top)*1.3
    assert 'ImageOps.pad(' in (ROOT/'app.py').read_text()


def test_logo_is_shown_whole_and_without_a_box_on_every_screen():
    css=(ROOT/'assets'/'navigation.css').read_text()
    rule=next(line for line in css.splitlines() if line.startswith('.st-key-open_home button::before{'))
    assert 'background-size:contain' in rule
    assert 'background-color' not in rule and 'box-shadow' not in rule and 'border' not in rule
    from streamlit.testing.v1 import AppTest
    at=AppTest.from_file(str(ROOT/'app.py')).run()
    welcome=next(element.proto.body for element in at.get('html') if 'welcome-mark' in element.proto.body)
    mark=welcome[welcome.index('.welcome-mark{'):];mark=mark[:mark.index('}')]
    assert 'object-fit:contain' in mark and 'background' not in mark and 'box-shadow' not in mark
