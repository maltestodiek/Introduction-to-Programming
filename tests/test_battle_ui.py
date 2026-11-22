from battle_ui import battle_progress_tiles, countdown_seconds, timer_fraction, timer_tick_fractions


def test_battle_progress_tiles_show_saved_outcomes_current_and_open_questions():
    tiles=battle_progress_tiles([
        {'index':0,'correct':True},
        {'index':1,'correct':False,'timed_out':True},
    ],2)
    assert [tile['state'] for tile in tiles[:4]]==['correct','incorrect','current','open']
    assert len(tiles)==15


def test_battle_timer_fraction_is_limited_to_the_server_timer_range():
    assert timer_fraction(15)==0.5
    assert timer_fraction(-1)==0
    assert timer_fraction(50)==1


def test_battle_timer_tick_moves_smoothly_to_the_next_server_second():
    assert timer_tick_fractions(26)==(26/30,25/30)
    assert timer_tick_fractions(0)==(0,0)


def test_battle_countdown_advances_locally_without_reloading_the_question():
    assert countdown_seconds(30,0)==30
    assert countdown_seconds(30,1.01)==29
    assert countdown_seconds(1,1)==0
    assert countdown_seconds(0,10)==0


def test_battle_rating_stays_open_and_recovers_from_failed_reads_and_writes(monkeypatch):
    from test_deck_ui import button, deck_app

    calls = []
    def action(_repo, name, data=None):
        calls.append(name)
        if name == 'round':
            if calls.count('round') == 1:
                raise ValueError('Could not load the round.')
            return {'state': 'rating', 'score': 7, 'can_rate': True}
        if name == 'rate' and calls.count('rate') == 1:
            raise ValueError('Could not save the rating.')
        return {'sessions': [], 'invites': []}

    monkeypatch.setattr('db.BattleRepository.action', action)
    app = deck_app(monkeypatch)
    app.session_state['main_page'] = 'Play'
    app.session_state['play_mode_preview'] = 'Battle'
    app.session_state['battle_rating_session'] = 'demo'
    app.run()
    assert app.error[0].value == 'Could not load the round.'
    assert not app.get('dialog')[0].proto.dialog.dismissible
    button(app, 'Retry loading rating').click().run()
    app.radio(key='battle_rating_demo').set_value('neutral').run()
    assert app.error[0].value == 'Could not save the rating.'
    button(app, 'Retry saving rating').click().run()
    assert 'battle_rating_session' not in app.session_state
    assert calls.count('rate') == 2
    assert not app.exception
