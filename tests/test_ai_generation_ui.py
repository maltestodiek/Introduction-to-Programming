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
