from test_deck_ui import deck_app,button


def row(rank,username,xp,me=False):return {'rank':rank,'username':username,'image_path':username+'/avatar.png','xp':xp,'me':me}


def setup(monkeypatch,data):
    monkeypatch.setattr('db.LeaderboardRepository.load',lambda self:data)
    at=deck_app(monkeypatch);button(at,'Leaderboard').click().run()
    return at


def texts(at):return [m.value for m in at.markdown]


def test_global_top_ten_with_own_place_below_when_outside(monkeypatch):
    top=[row(i+1,f'player{i+1}',1000-i*50) for i in range(10)]
    at=setup(monkeypatch,{'top':top,'me':row(37,'student_a',15,True),'friends':[row(1,'student_a',15,True)]})
    shown=texts(at)
    assert at.title[0].value=='Leaderboard' and [t.label for t in at.tabs]==['Global top 10','Friends']
    for place,name,points in [('#1','player1','1000 XP'),('#10','player10','550 XP')]:
        assert place in shown and name in shown and points in shown
    assert '**#37**' in shown and '**student_a (you)**' in shown and '**15 XP**' in shown
    assert any(c.value=='Your place' for c in at.caption)
    assert shown.index('player10')<shown.index('**student_a (you)**')
    assert any('Add friends' in c.value for c in at.caption)
    assert not any(i.value=='Coming soon' for i in at.info)
    assert not at.exception


def test_inside_top_ten_is_marked_once_and_friends_are_ranked(monkeypatch):
    top=[row(1,'anna',500),row(2,'student_a',400,True),row(2,'cleo',400)]
    at=setup(monkeypatch,{'top':top,'me':row(2,'student_a',400,True),'friends':[row(1,'student_a',400,True),row(2,'ben',120)]})
    shown=texts(at)
    assert shown.count('**student_a (you)**')==2  # once in each ranking, no extra row below the global list
    assert not any(c.value=='Your place' for c in at.caption) and not any('Add friends' in c.value for c in at.caption)
    assert 'ben' in shown and '120 XP' in shown
    assert not at.exception


def test_leaderboard_is_read_only_and_reports_problems(monkeypatch):
    at=setup(monkeypatch,{'top':[row(1,'anna',500)],'me':row(2,'student_a',0,True),'friends':[row(1,'student_a',0,True)]})
    labels=[b.label for b in at.button]
    assert not any(word in label.lower() for label in labels for word in ('invite','add friend','chat with','message','code'))
    assert not at.text_input and not at.get('link_button')
    def broken(self):raise ValueError('The leaderboard could not be reached. Refresh and retry.')
    monkeypatch.setattr('db.LeaderboardRepository.load',broken);at.run()
    assert any('could not be reached' in e.value for e in at.error) and not at.exception
