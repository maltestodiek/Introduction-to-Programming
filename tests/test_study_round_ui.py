from study_ui import study_progress_tiles


def test_study_progress_tiles_show_saved_outcomes_current_and_open_questions():
    tiles=study_progress_tiles([{'index':0,'correct':True},{'index':1,'correct':False}],2,5)
    assert [tile['state'] for tile in tiles]==['correct','incorrect','current','open','open']


def test_the_study_round_offers_a_private_note_but_no_author_feedback_field():
    from pathlib import Path
    app=(Path(__file__).parents[1]/'app.py').read_text()
    assert 'Feedback for the author' not in app
    assert 'study_send_' not in app and 'study_feedback_' not in app
    section=app[app.index("with st.expander('Private note')"):app.index("if st.button('Next question'")]
    assert 'study_note_' in section and "'annotate'" in section
    # The author side keeps showing received feedback.
    assert "with st.expander('Feedback on your questions')" in app
    assert "Feedback you sent: " in app
