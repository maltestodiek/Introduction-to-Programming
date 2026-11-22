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


def test_study_round_aligns_the_overview_with_the_question_card_and_uses_the_standard_side_panel_width():
    from pathlib import Path
    app=(Path(__file__).parents[1]/'app.py').read_text()
    section=app[app.index('def study_round_screen'):app.index('def study_plan_screen')]
    # Progress captions sit above the two columns, leaving both the question card
    # and its overview to start on the same horizontal line.
    assert section.index("st.caption(f\"Question {r['index']+1} of {r['total']}\")") < section.index("question,overview=st.columns([3,2],gap='large')")
    assert section.index("question,overview=st.columns([3,2],gap='large')") < section.index("with overview:")


def test_matched_study_round_keeps_the_deadline_explanation_in_a_save_and_leave_info_control():
    from pathlib import Path
    app=(Path(__file__).parents[1]/'app.py').read_text()
    section=app[app.index('def study_round_screen'):app.index('def study_plan_screen')]
    assert "help='Session deadline'" in section
    assert "You can leave and resume until " in section
    overview=section[section.index('with overview:'):section.index('with question:')]
    assert "with st.container(border=True, key='study_round_overview_'+sid):" in overview
    assert "st.button('Save and leave Study session', key='study_save_leave_'+sid," in overview
    assert "icon=':material/save:', width='stretch'" in overview
    assert "study_stop_control(client, sid, in_round=True)" in overview
    assert "help='Session deadline'" not in overview
    assert section.index("help='Session deadline'") < section.index("question,overview=st.columns([3,2],gap='large')")
    question_layout=section[section.index("if state=='question':"):section.index("question,overview=st.columns([3,2],gap='large')")]
    assert "r['part']" not in question_layout
    assert "Finish by " not in question_layout


def test_study_overview_extends_its_single_card_to_include_session_actions():
    from pathlib import Path
    css=(Path(__file__).parents[1]/'assets'/'study-round.css').read_text()
    assert '[class*="st-key-study_round_overview_"]{position:sticky' in css
    assert '.study-overview{background:transparent;border:0' in css
    assert '.study-overview-actions-divider' in css
    assert '[class*="st-key-study_save_leave_"] button' in css
    assert '[class*="st-key-study_stop_confirm_"] button{border-color:transparent' in css
