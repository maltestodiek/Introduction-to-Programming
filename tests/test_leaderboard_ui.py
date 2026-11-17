import re
from test_deck_ui import deck_app,button

ROW=re.compile(r'<div class="sd-lb-row( sd-lb-me)?"><span class="sd-lb-place">#(\d+)</span><img [^>]*><span class="sd-lb-name">(.*?)</span><span class="sd-lb-xp">(\d+) XP</span></div>')


def row(rank,username,xp,me=False):return {'rank':rank,'username':username,'image_path':username+'/avatar.png','xp':xp,'me':me}


def setup(monkeypatch,data):
    monkeypatch.setattr('db.LeaderboardRepository.load',lambda self:data)
    at=deck_app(monkeypatch);button(at,'Leaderboard').click().run()
    return at


def lists(at):
    """Each ranking on the page as [(place, name, xp, marked as own row)], in the order shown."""
    bodies=[h.proto.body for h in at.get('html') if 'sd-lb-row' in h.proto.body]
    return [[(int(place),name,int(xp),bool(me)) for me,place,name,xp in ROW.findall(body)] for body in bodies]


def test_global_top_ten_with_own_place_below_when_outside(monkeypatch):
    top=[row(i+1,f'player{i+1}',1000-i*50) for i in range(10)]
    at=setup(monkeypatch,{'top':top,'me':row(37,'student_a',15,True),'friends':[row(1,'student_a',15,True)]})
    world,own,friends=lists(at)
    assert at.title[0].value=='Leaderboard' and [t.label for t in at.tabs]==['Global top 10','Friends']
    assert len(world)==10 and world[0]==(1,'player1',1000,False) and world[9]==(10,'player10',550,False)
    assert own==[(37,'student_a (you)',15,True)] and friends==[(1,'student_a (you)',15,True)]
    assert any(c.value=='Your place' for c in at.caption) and any('Add friends' in c.value for c in at.caption)
    assert not any(i.value=='Coming soon' for i in at.info)
    assert not at.exception


def test_inside_top_ten_is_marked_once_and_friends_are_ranked(monkeypatch):
    top=[row(1,'anna',500),row(2,'student_a',400,True),row(2,'cleo',400)]
    at=setup(monkeypatch,{'top':top,'me':row(2,'student_a',400,True),'friends':[row(1,'student_a',400,True),row(2,'ben',120)]})
    world,friends=lists(at)  # no extra own row below the global list
    assert world==[(1,'anna',500,False),(2,'student_a (you)',400,True),(2,'cleo',400,False)]
    assert friends==[(1,'student_a (you)',400,True),(2,'ben',120,False)]
    assert not any(c.value=='Your place' for c in at.caption) and not any('Add friends' in c.value for c in at.caption)
    assert not at.exception


def test_leaderboard_is_read_only_escapes_names_and_reports_problems(monkeypatch):
    at=setup(monkeypatch,{'top':[row(1,'<b>anna</b>',500)],'me':row(2,'student_a',0,True),'friends':[row(1,'student_a',0,True)]})
    assert lists(at)[0]==[(1,'&lt;b&gt;anna&lt;/b&gt;',500,False)]
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
    world,own,friends=lists(at)
    assert any('invented students' in w.value for w in at.warning)
    assert world[0]==(1,'nora_k',1840,False) and [place for place,*_ in world[:5]]==[1,2,3,3,5] and len(world)==10
    assert own==[(11,'student_a (you)',705,True)] and any(c.value=='Your place' for c in at.caption)
    assert [name for _,name,_,_ in friends]==['tiago','ines','student_a (you)','emma_w','hugo']
    assert not at.exception


def test_preview_switch_is_ignored_outside_a_local_copy(monkeypatch):
    monkeypatch.setenv('LEADERBOARD_DEMO','1');monkeypatch.setenv('APP_URL','https://studyduel-nova-main.streamlit.app')
    monkeypatch.setattr('db.LeaderboardRepository.load',lambda self:{'top':[row(1,'student_a',5,True)],'me':row(1,'student_a',5,True),'friends':[row(1,'student_a',5,True)]})
    at=deck_app(monkeypatch);button(at,'Leaderboard').click().run()
    assert not at.warning and lists(at)[0]==[(1,'student_a (you)',5,True)]
    assert not at.exception
