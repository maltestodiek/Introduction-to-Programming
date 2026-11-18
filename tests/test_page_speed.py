import base64
import io
from pathlib import Path

from PIL import Image

from logic import DEFAULT_AVATAR, render_avatar
from page_speed import ProfileCache, logo_variants, should_verify, thumbnail
from test_deck_ui import deck_app

ROOT=Path(__file__).parents[1]
LOGO=ROOT/'assets'/'uniarena-icon.png'


def test_logo_copies_are_much_smaller_and_keep_their_shape():
    full=len(base64.b64encode(LOGO.read_bytes()))
    copies=logo_variants(str(LOGO),LOGO.stat().st_mtime)
    assert len(copies['small'])<full/8 and len(copies['medium'])<full/1.5
    original=Image.open(LOGO)
    for name,width in (('small',224),('medium',680)):
        image=Image.open(io.BytesIO(base64.b64decode(copies[name])))
        assert image.width==width and image.mode=='RGBA'
        assert abs(image.width/image.height-original.width/original.height)<0.02
        assert image.getpixel((0,0))[3]==0  # still transparent


def test_thumbnail_is_small_square_and_falls_back_to_the_original_on_bad_data():
    avatar=render_avatar(DEFAULT_AVATAR)
    small=thumbnail(avatar,84)
    assert Image.open(io.BytesIO(small)).size==(84,84) and len(small)<len(avatar)/4
    assert thumbnail(b'not an image',84)==b'not an image'


def test_profile_cache_reuses_reads_briefly_and_never_serves_another_user():
    loads=[]
    def load():
        loads.append(1);return {'username':'a','n':len(loads)}
    cache=ProfileCache(seconds=20)
    assert cache.get('a',load,now=100)['n']==1
    assert cache.get('a',load,now=110)['n']==1          # reused
    assert cache.get('a',load,now=110,fresh=True)['n']==2  # Profile page, editing, after a save
    assert cache.get('a',load,now=131)['n']==3          # too old
    assert cache.get('b',load,now=132)['n']==4          # different user
    cache.clear();assert cache.get('b',load,now=133)['n']==5


def test_profile_cache_does_not_keep_a_missing_profile():
    answers=[None,{'username':'a'}]
    cache=ProfileCache(seconds=20)
    assert cache.get('a',lambda:answers.pop(0),now=1) is None
    assert cache.get('a',lambda:answers.pop(0),now=2)=={'username':'a'}


def test_sign_in_is_confirmed_at_most_once_a_minute():
    assert should_verify(now=1000,last=None)
    assert not should_verify(now=1000,last=950)
    assert should_verify(now=1000,last=939)
    assert should_verify(now=1000,last=2000)  # a clock that went backwards must not skip the check


def html_bytes(at):
    return sum(len(element.proto.body) for element in at.get('html'))


def test_a_normal_page_sends_far_less_image_data(monkeypatch):
    at=deck_app(monkeypatch)
    full_logo=base64.b64encode(LOGO.read_bytes()).decode()
    bodies=[element.proto.body for element in at.get('html')]
    assert not any(full_logo in body for body in bodies)
    assert not any(base64.b64encode(render_avatar(DEFAULT_AVATAR)).decode() in body for body in bodies)
    assert html_bytes(at)<170_000  # was about 590,000 with the full-size logo and avatar
    assert not at.exception


def test_browsing_reads_the_profile_once_but_the_profile_page_reads_it_fresh(monkeypatch):
    from logic import DEFAULT_AVATAR as avatar
    loads=[]
    profile={'username':'student_a','university':'Example University','courses':['Finance'],'languages':['English'],'avatar':avatar,'image_mode':'Avatar'}
    at=deck_app(monkeypatch)
    monkeypatch.setattr('db.ProfileRepository.load',lambda self:loads.append(1) or profile)
    monkeypatch.setattr('db.FriendsRepository.action',lambda self,action,value='':{'code':'AB23CD45','friends':[],'incoming':[],'sent':[],'invite_expires':None})
    for label in ('Leaderboard','Decks','Leaderboard'):
        next(b for b in at.button if b.label==label).click().run()
    assert len(loads)==0  # the read from opening the app is reused
    next(b for b in at.button if b.label=='Profile').click().run()
    assert len(loads)>=1  # the Profile page always shows current figures
    assert not at.exception


def test_the_signed_in_user_is_not_reconfirmed_on_every_click(monkeypatch):
    at=deck_app(monkeypatch)
    client=at.session_state['auth'].client
    first=client.auth.get_user.call_count
    for label in ('Leaderboard','Decks','Leaderboard'):
        next(b for b in at.button if b.label==label).click().run()
    assert client.auth.get_user.call_count==first
    assert not at.exception


def test_a_session_that_fails_confirmation_still_ends(monkeypatch):
    from types import SimpleNamespace as Obj
    at=deck_app(monkeypatch)
    client=at.session_state['auth'].client
    client.auth.get_user.return_value=Obj(user=None)
    at.session_state['verified_at']=0  # the next check is due
    next(b for b in at.button if b.label=='Leaderboard').click().run()
    assert any('session has ended' in w.value for w in at.warning)
    assert at.session_state['auth'].user is None
