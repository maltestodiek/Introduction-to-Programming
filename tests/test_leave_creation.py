from pathlib import Path

ROOT=Path(__file__).parents[1]
APP=(ROOT/'app.py').read_text()


def test_every_creation_flow_warns_before_dropping_unsaved_content():
    assert "leave_creation_control('Back to Decks','anki_import_back'" in APP
    assert "leave_creation_control('Back to Decks','pdf_import_back'" in APP
    assert "leave_creation_control('Leave Study editor','study_editor_leave',True" in APP
    helper=APP[APP.index('def leave_creation_control'):APP.index('def anki_import_screen')]
    assert 'Leave without saving?' in helper
    assert "st.container(key=f'round_leave_modal_{key}')" in helper
    assert 'round-modal-backdrop' in helper
    assert 'Keep working' in helper and 'Leave and discard' in helper


def test_leaving_without_parsed_content_needs_no_confirmation():
    assert "bool(st.session_state.get('anki_import_result')) and not st.session_state.get('anki_import_saved')" in APP
    assert "bool(st.session_state.get('pdf_import_result')) and not st.session_state.get('pdf_import_saved')" in APP
    helper=APP[APP.index('def leave_creation_control'):APP.index('def anki_import_screen')]
    assert 'if has_unsaved:' in helper


def test_the_old_unguarded_exits_are_gone():
    assert 'Discard unsaved Study changes' not in APP
    assert APP.count("anki_import_reset();st.session_state.pop('anki_import_open',None)")==1
