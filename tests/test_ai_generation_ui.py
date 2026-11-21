from test_deck_ui import button, deck_app

IMPORT={
    'id':'import-1','name':'Finance notes','course':'Finance','language':'English',
    'cards':[{'id':'card-1','front':'What is NPV?','back':'Net present value'}],
    'drafts':[],
}


def generation_app(monkeypatch,calls,result=None,error=None):
    monkeypatch.setattr('db.AnkiImportRepository.imports',lambda self:[IMPORT])
    def generate(self,import_id,card_ids):
        calls.append((import_id,list(card_ids)))
        if error:raise ValueError(error)
        return result or {'count':len(card_ids),'status':'draft'}
    monkeypatch.setattr('db.AnkiImportRepository.generate',generate)
    at=deck_app(monkeypatch)
    at.session_state['anki_generation_open']=True
    at.run()
    return at


def test_one_click_starts_exactly_one_generation(monkeypatch):
    calls=[]
    at=generation_app(monkeypatch,calls)
    at.checkbox(key='anki_source_card-1').check().run()
    button(at,'Generate 1 question drafts').click().run()
    assert calls==[('import-1',['card-1'])]
    at.run()
    assert calls==[('import-1',['card-1'])]
    assert 'ai_generation_request' not in at.session_state
    assert not at.exception


def test_pending_generation_request_runs_exactly_once(monkeypatch):
    calls=[]
    at=generation_app(monkeypatch,calls)
    at.checkbox(key='anki_source_card-1').check().run()
    at.session_state['ai_generation_request']={'import_id':'import-1','card_ids':['card-1']}
    at.run()
    assert calls==[('import-1',['card-1'])]
    assert 'ai_generation_request' not in at.session_state
    at.run()
    assert len(calls)==1


def test_failed_generation_shows_the_error_and_allows_a_new_attempt(monkeypatch):
    calls=[]
    at=generation_app(monkeypatch,calls,error='The AI provider took too long to respond.')
    at.checkbox(key='anki_source_card-1').check().run()
    button(at,'Generate 1 question drafts').click().run()
    assert any('took too long' in item.value for item in at.error)
    assert not button(at,'Generate 1 question drafts').disabled
    assert 'ai_generation_request' not in at.session_state


def test_publishing_drafts_creates_the_study_deck_without_the_editor_detour():
    from pathlib import Path
    app=(Path(__file__).parents[1]/'app.py').read_text()
    assert 'Create editable Study deck' not in app
    assert 'ai_draft_ids' not in app
    section=app[app.index("st.subheader('3. Publish Study deck')"):app.index('def play_request')]
    order=[section.index("study_request(client,'review_deck',{'draft':clean,'revision':0})"),
           section.index("study_request(client,'save_deck',{'draft':clean,'revision':0,'review_id':review['id']})"),
           section.index('repository.publish_drafts(')]
    assert order==sorted(order)
    assert 'validate_study_deck' in section


def test_notice_precedes_sending_private_material(monkeypatch):
    calls = []
    at = generation_app(monkeypatch, calls)
    assert any('Requesty' in c.value and 'model provider' in c.value and
               'selected' in c.value.lower() for c in at.caption)
    assert calls == []


def test_unsaved_correction_blocks_publishing_until_saved(monkeypatch):
    draft = dict(id='draft-1', source_card_id='card-1', status='draft',
                 question='What is NPV?', options=['Revenue', 'Net present value', 'Cost', 'Tax'],
                 correct_option_index=0)
    monkeypatch.setitem(IMPORT, 'drafts', [draft])
    saved_decks = []

    def save_edit(self, draft_id, question, options, correct):
        assert draft_id == draft['id']
        draft.update(question=question, options=options, correct_option_index=correct)

    def study_action(self, action, data=None):
        if action == 'review_deck':
            return {'id': 'review-1'}
        if action == 'save_deck':
            saved_decks.append(data['draft'])
            return {'id': 'deck-1'}
        return {'decks': [], 'shared': [], 'sessions': [], 'open': [], 'invites': [], 'friends': []}

    monkeypatch.setattr('db.AnkiImportRepository.update_draft', save_edit)
    monkeypatch.setattr('db.AnkiImportRepository.publish_drafts', lambda self, ids: None)
    monkeypatch.setattr('db.StudyRepository.action', study_action)
    at = generation_app(monkeypatch, [])
    at.checkbox(key='ai_include_draft-1').check().run()
    publish = 'Publish Study deck from 1 drafts'
    assert not button(at, publish).disabled
    at.radio(key='ai_correct_draft-1').set_value(1).run()
    assert button(at, publish).disabled
    assert any('Save edits' in w.value for w in at.warning)
    assert not saved_decks
    at.button(key='ai_save_draft-1').click().run()
    assert not button(at, publish).disabled
    button(at, publish).click().run()
    card = saved_decks[0]['cards'][0]
    assert next(a['text'] for a in card['answers'] if a['id'] == card['correct_answer_id']) == 'Net present value'
