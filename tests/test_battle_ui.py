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
