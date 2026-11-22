from test_deck_ui import deck_app

from profile_summary import profile_stats_html


def test_stats_row_holds_the_three_figures_with_the_xp_breakdown():
    html=profile_stats_html({'total':22,'battle':22},3,4)
    for part in ('Battle XP','>22<','Win streak','>3<','Friends','>4<'):
        assert part in html
    assert 'Total XP' not in html
    assert html.index('Battle XP')<html.index('Win streak')<html.index('Friends')
    assert 'aria-label="Profile figures"' in html


def test_friends_shows_a_dash_when_the_list_is_unavailable_and_values_are_escaped():
    html=profile_stats_html({'total':0,'battle':0},0,None)
    assert '>—<' in html
    assert '<script>' not in profile_stats_html({'total':'<script>','battle':0},0,1)


def profile_page(monkeypatch,friends):
    monkeypatch.setattr('db.FriendsRepository.action',friends)
    at=deck_app(monkeypatch)
    at.session_state['main_page']='Profile'
    return at.run()


def test_profile_shows_the_figures_beside_the_avatar_and_no_large_cards(monkeypatch):
    at=profile_page(monkeypatch,lambda self,action,value='':{'code':'AB23CD45','friends':[{'id':'e','person':{'id':'b','username':'student_b','image_path':None}}],'incoming':[],'sent':[],'invite_expires':None})
    assert not at.exception
    assert len(at.metric)==0
    bodies=[element.proto.body for element in at.get('html')]
    stats=next(body for body in bodies if 'sd-profile-stats' in body)
    assert 'Friends' in stats and '>1<' in stats and 'Win streak' in stats and 'Battle XP' in stats
    assert not any('sd-xp-summary"' in body for body in bodies)
    # the row sits in the summary beside the avatar: after the username heading and before the courses
    name=next(i for i,body in enumerate(bodies) if 'student_a' in body and '<h1' in body)
    assert bodies.index(stats)==name+1


def test_profile_still_opens_when_the_friends_list_is_unavailable(monkeypatch):
    def unavailable(self,action,value=''):raise ValueError('Could not load your friends. Refresh and try again.')
    at=profile_page(monkeypatch,unavailable)
    assert not at.exception
    assert any('>—<' in element.proto.body for element in at.get('html') if 'sd-profile-stats' in element.proto.body)


def courses_profile(monkeypatch,shared=('Corporate Finance','Investments')):
    from pathlib import Path
    from types import SimpleNamespace as Obj
    from unittest.mock import Mock
    from streamlit.testing.v1 import AppTest
    from auth import AuthService
    from logic import DEFAULT_AVATAR
    profile={'username':'student_a','university':'Example University','courses':['Private Equity'],'languages':['English'],'avatar':DEFAULT_AVATAR,
             'image_mode':'Avatar','image_path':'a/current.png','degree':"Master's",'area':'Finance','graduation_year':2027}
    monkeypatch.setattr('db.ProfileRepository.load',lambda self:profile)
    monkeypatch.setattr('db.FriendsRepository.action',lambda self,action,value='':{'code':'AB23CD45','friends':[],'incoming':[],'sent':[],'invite_expires':None})
    client=Mock();client.auth.get_user.return_value=Obj(user=Obj(id='a'))
    def rpc(name,args=None):
        call=Mock();call.execute.return_value.data=list(shared) if name=='university_courses' else None
        return call
    client.rpc.side_effect=rpc
    auth=AuthService(client);auth.user=client.auth.get_user.return_value.user
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=15)
    at.session_state['auth']=auth;at.session_state['main_page']='Profile'
    return at.run(),client


def test_profile_displays_degree_and_field_under_the_university(monkeypatch):
    at, _ = courses_profile(monkeypatch)
    assert not at.exception
    assert any(
        'Example University' in element.proto.body and 'Master in Finance' in element.proto.body
        for element in at.get('html')
    )


def saves(client):
    return [c.args[1] for c in client.rpc.call_args_list if c.args[0].startswith('save_profile')]


def test_profile_offers_add_courses_instead_of_open_friends(monkeypatch):
    at,client=courses_profile(monkeypatch)
    labels=[b.label for b in at.button]
    assert 'Add courses' in labels and 'Open friends' not in labels
    assert not any(w.label=='Your courses' for w in at.multiselect)  # the editor opens only on request
    assert not at.exception


def test_add_courses_uses_the_shared_list_and_saves_only_the_courses(monkeypatch):
    at,client=courses_profile(monkeypatch)
    next(b for b in at.button if b.label=='Add courses').click().run()
    editor=next(w for w in at.multiselect if w.label=='Your courses')
    assert list(editor.options)==['Corporate Finance','Investments','Private Equity'] and list(editor.value)==['Private Equity']
    editor.set_value(['Private Equity','corporate  finance'])
    next(b for b in at.button if b.label=='Save courses').click().run()
    assert not at.exception
    saved=saves(client)
    assert len(saved)==1 and saved[0]['p_courses']==['Private Equity','Corporate Finance']
    # everything else is sent back unchanged, and no new image is uploaded
    assert (saved[0]['p_username'],saved[0]['p_university'],saved[0]['p_languages'],saved[0]['p_degree'],saved[0]['p_area'],saved[0]['p_graduation_year'])==('student_a','Example University',['English'],"Master's",'Finance',2027)
    assert saved[0]['p_image_mode']=='Avatar' and saved[0]['p_image_path']=='a/current.png'
    client.storage.from_.return_value.upload.assert_not_called()
    assert not any(w.label=='Your courses' for w in at.multiselect)  # the editor closes after saving


def test_removing_every_course_is_rejected_and_cancel_changes_nothing(monkeypatch):
    at,client=courses_profile(monkeypatch)
    next(b for b in at.button if b.label=='Add courses').click().run()
    next(w for w in at.multiselect if w.label=='Your courses').set_value([])
    next(b for b in at.button if b.label=='Save courses').click().run()
    assert any('course' in e.value.lower() for e in at.error) and saves(client)==[]
    next(b for b in at.button if b.label=='Cancel').click().run()
    assert not any(w.label=='Your courses' for w in at.multiselect) and saves(client)==[]
    assert not at.exception
