from study_ui import study_progress_tiles


def test_study_progress_tiles_show_saved_outcomes_current_and_open_questions():
    tiles=study_progress_tiles([{'index':0,'correct':True},{'index':1,'correct':False}],2,5)
    assert [tile['state'] for tile in tiles]==['correct','incorrect','current','open','open']
