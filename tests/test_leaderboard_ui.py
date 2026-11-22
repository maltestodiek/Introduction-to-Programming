import re
from test_deck_ui import deck_app,button

ROW=re.compile(r'<div class="sd-lb-row( sd-lb-me)?"><span class="sd-lb-place">#(\d+)</span><img [^>]*><span class="sd-lb-identity"><span class="sd-lb-name">(.*?)</span><span class="sd-lb-university">(.*?)</span></span><span class="sd-lb-xp">(\d+) XP</span></div>')


def row(rank,username,xp,me=False,university='Nova SBE'):return {'rank':rank,'username':username,'university':university,'image_path':username+'/avatar.png','xp':xp,'me':me}


def setup(monkeypatch,data):
    monkeypatch.setattr('db.LeaderboardRepository.load',lambda self:data)
    monkeypatch.setattr('db.LeaderboardRepository.university_top',lambda self,viewer:data.get('university',[]))
    at=deck_app(monkeypatch);button(at,'Leaderboard').click().run()
    return at


def lists(at):
    """Each ranking on the page as [(place, name, university, xp, own row)], in the order shown."""
    bodies=[h.proto.body for h in at.get('html') if 'sd-lb-row' in h.proto.body]
    return [[(int(place),name,university,int(xp),bool(me)) for me,place,name,university,xp in ROW.findall(body)] for body in bodies]


def test_global_top_ten_with_own_place_below_when_outside(monkeypatch):
    top=[row(i+1,f'player{i+1}',1000-i*50) for i in range(10)]
    at=setup(monkeypatch,{'top':top,'me':row(37,'student_a',15,True),'friends':[row(1,'student_a',15,True)]})
    world,own,friends=lists(at)
    assert at.title[0].value=='Leaderboard' and [t.label for t in at.tabs]==['Global top 10','University top 10','Friends']
    assert len(world)==10 and world[0]==(1,'player1','Nova SBE',1000,False) and world[9]==(10,'player10','Nova SBE',550,False)
    assert own==[(37,'student_a (you)','Nova SBE',15,True)] and friends==[(1,'student_a (you)','Nova SBE',15,True)]
    assert any(c.value=='Your place' for c in at.caption) and any('Add friends' in c.value for c in at.caption)
    assert not any(i.value=='Coming soon' for i in at.info)
    assert not at.exception


def test_inside_top_ten_is_marked_once_and_friends_are_ranked(monkeypatch):
    top=[row(1,'anna',500),row(2,'student_a',400,True),row(2,'cleo',400)]
    at=setup(monkeypatch,{'top':top,'me':row(2,'student_a',400,True),'friends':[row(1,'student_a',400,True),row(2,'ben',120)]})
    world,friends=lists(at)  # no extra own row below the global list
    assert world==[(1,'anna','Nova SBE',500,False),(2,'student_a (you)','Nova SBE',400,True),(2,'cleo','Nova SBE',400,False)]
    assert friends==[(1,'student_a (you)','Nova SBE',400,True),(2,'ben','Nova SBE',120,False)]
    assert not any(c.value=='Your place' for c in at.caption) and not any('Add friends' in c.value for c in at.caption)
    assert not at.exception


def test_leaderboard_is_read_only_escapes_names_and_reports_problems(monkeypatch):
    at=setup(monkeypatch,{'top':[row(1,'<b>anna</b>',500)],'me':row(2,'student_a',0,True),'friends':[row(1,'student_a',0,True)]})
    assert lists(at)[0]==[(1,'&lt;b&gt;anna&lt;/b&gt;','Nova SBE',500,False)]
    labels=[b.label for b in at.button]
    assert not any(word in label.lower() for label in labels for word in ('invite','add friend','chat with','message','code'))
    assert not at.text_input and not at.get('link_button')
    assert not any('<a ' in h.proto.body or '<button' in h.proto.body for h in at.get('html') if 'sd-lb-row' in h.proto.body)
    def broken(self):raise ValueError('The leaderboard could not be reached. Refresh and retry.')
    monkeypatch.setattr('db.LeaderboardRepository.load',broken);at.run()
    assert any('could not be reached' in e.value for e in at.error) and not at.exception


def test_local_preview_uses_invented_students_and_never_the_database(monkeypatch):
    def forbidden(self):raise AssertionError('the preview must not read the database')
    monkeypatch.setattr('db.LeaderboardRepository.load',forbidden)
    monkeypatch.setenv('LEADERBOARD_DEMO','1')
    at=deck_app(monkeypatch);button(at,'Leaderboard').click().run()
    world,own,campus,friends=lists(at)
    assert campus==[(1,'student_a (you)','Example University',705,True)]
    assert any('invented students' in w.value for w in at.warning)
    assert world[0]==(1,'nora_k','Nova SBE',1840,False) and [place for place,*_ in world[:5]]==[1,2,3,3,5] and len(world)==10
    assert own==[(11,'student_a (you)','Example University',705,True)] and any(c.value=='Your place' for c in at.caption)
    assert [name for _,name,*_ in friends]==['tiago','ines','student_a (you)','emma_w','hugo']
    assert not at.exception


def test_preview_switch_is_ignored_outside_a_local_copy(monkeypatch):
    monkeypatch.setenv('LEADERBOARD_DEMO','1');monkeypatch.setenv('APP_URL','https://studyduel-nova-main.streamlit.app')
    monkeypatch.setattr('db.LeaderboardRepository.load',lambda self:{'top':[row(1,'student_a',5,True)],'me':row(1,'student_a',5,True),'friends':[row(1,'student_a',5,True)]})
    at=deck_app(monkeypatch);button(at,'Leaderboard').click().run()
    assert not at.warning and lists(at)[0]==[(1,'student_a (you)','Nova SBE',5,True)]
    assert not at.exception


def test_university_middle_tab_shows_only_its_own_standings(monkeypatch):
    at=setup(monkeypatch,{
        'top':[row(1,'world_champion',900,university='Other University')],
        'me':row(17,'student_a',80,True),
        'university':[row(1,'classmate',90),row(2,'student_a',80,True)],
        'friends':[row(1,'student_a',80,True)],
    })
    campus=at.tabs[1]
    assert campus.label=='University top 10'
    assert lists(campus)==[[(1,'classmate','Nova SBE',90,False),(2,'student_a (you)','Nova SBE',80,True)]]
    assert not campus.selectbox and not campus.text_input


def test_university_query_filters_before_limiting_and_ranks_ties():
    from unittest.mock import Mock
    from db import LeaderboardRepository
    client=Mock()
    query=client.table.return_value
    for method in ('select','eq','order','limit'):
        getattr(query,method).return_value=query
    query.execute.return_value.data=[
        {'username':name,'game_xp':xp,'image_path':None}
        for name,xp in [('alice',100),('ben',100),('cleo',70)]
    ]
    repo=LeaderboardRepository(client)
    result=repo.university_top({'username':'ben','university':'Nova SBE'})
    client.table.assert_called_once_with('profiles')
    assert [str(call) for call in query.method_calls]==[
        "call.select('username,image_path,game_xp')", "call.eq('university', 'Nova SBE')",
        "call.order('game_xp', desc=True)", "call.order('username')", "call.limit(10)", "call.execute()",
    ]
    assert [(r['username'],r['rank'],r['me']) for r in result]==[('alice',1,False),('ben',1,True),('cleo',3,False)]
    client.reset_mock()
    assert repo.university_top({'university':'', 'username':'ben'})==[]
    client.table.assert_not_called()

def test_all_rankings_use_one_30_day_response_and_explain_expiry(monkeypatch):
    from db import LeaderboardRepository
    from unittest.mock import Mock
    me = row(1, 'student_a', 40, True)
    data = {'top': [me], 'university': [me], 'friends': [me], 'me': me}
    client = Mock()
    client.rpc.return_value.execute.return_value.data = data
    assert LeaderboardRepository(client).load() == data
    client.rpc.assert_called_once_with('leaderboard_30_days', {})
    def reject_lifetime_query(*args):
        raise AssertionError('All three tabs must use the rolling score')
    monkeypatch.setattr('db.LeaderboardRepository.load', lambda self: data)
    monkeypatch.setattr('db.LeaderboardRepository.university_top', reject_lifetime_query)
    at = deck_app(monkeypatch)
    button(at, 'Leaderboard').click().run()
    assert not at.exception
    assert len(lists(at)) == 3
    note = ' '.join(c.value.lower() for c in at.caption)
    assert 'last 30 days' in note and 'lifetime' in note and 'profile' in note
    assert not at.selectbox and not at.radio
