from battle_ui import battle_progress_tiles, timer_fraction


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
