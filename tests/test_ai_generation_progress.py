import time

import pytest

from logic import ai_generation_estimate_seconds, ai_generation_progress
from test_ai_generation_ui import generation_app
from test_deck_ui import button


@pytest.mark.parametrize('cards,seconds',[(1,45),(10,45),(11,45),(50,45),(51,80),(100,80)])
def test_estimate_follows_parallel_batch_rounds(cards,seconds):
    # Batches of 10 cards, five at once, about 35 seconds per round plus start-up.
    assert ai_generation_estimate_seconds(cards)==seconds


def test_progress_grows_with_time_but_never_claims_completion():
    estimate=ai_generation_estimate_seconds(40)
    values=[ai_generation_progress(elapsed,estimate)[0] for elapsed in (0,10,30,estimate,estimate*3)]
    assert values==sorted(values)
    assert values[0]==0
    assert all(value<1 for value in values)
    assert values[-1]==pytest.approx(.95)


def test_progress_text_counts_down_and_then_says_almost_done():
    estimate=ai_generation_estimate_seconds(100)
    assert ai_generation_progress(0,estimate)[1]=='About 1 min 20 s left'
    assert ai_generation_progress(estimate-20,estimate)[1]=='About 20 s left'
    assert ai_generation_progress(estimate+5,estimate)[1]=='Almost done. Finishing the last questions…'


def test_slow_generation_shows_progress_and_finishes_once(monkeypatch):
    calls=[]
    at=generation_app(monkeypatch,calls)
    def slow_generate(self,import_id,card_ids):
        calls.append((import_id,list(card_ids)));time.sleep(1.2)
        return {'count':len(card_ids),'status':'draft'}
    monkeypatch.setattr('db.AnkiImportRepository.generate',slow_generate)
    at.checkbox(key='anki_source_card-1').check().run()
    button(at,'Generate 1 question drafts').click().run()
    assert calls==[('import-1',['card-1'])]
    assert not at.exception
    assert 'ai_generation_request' not in at.session_state
