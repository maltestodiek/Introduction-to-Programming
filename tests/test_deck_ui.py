from pathlib import Path
from unittest.mock import Mock
from types import SimpleNamespace as Obj
from streamlit.testing.v1 import AppTest
from auth import AuthService
from logic import DEFAULT_AVATAR
from test_deck_rules import complete_deck


def deck_app(monkeypatch):
    profile={'username':'student_a','university':'Example University','courses':['Finance'],'languages':['English'],'avatar':DEFAULT_AVATAR,'image_mode':'Avatar'}
    monkeypatch.setattr('db.ProfileRepository.load',lambda self:profile)
    monkeypatch.setattr('db.DeckRepository.list',lambda self,course:[])
    client=Mock();client.auth.get_user.return_value=Obj(user=Obj(id='a'))
    auth=AuthService(client);auth.user=client.auth.get_user.return_value.user
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=20)
    at.session_state['auth']=auth;at.session_state['main_page']='Decks';at.run()
    return at

def button(at,label):return next(b for b in at.button if b.label==label)

def test_placeholders_disabled_and_incomplete_card_rejected(monkeypatch):
    at=deck_app(monkeypatch)
    assert button(at,'Import from Anki').disabled
    assert button(at,'Generate with AI').disabled
    button(at,'+ Create New Deck').click().run()
    assert button(at,'Save Deck').disabled
    button(at,'+ Add Flashcard').click().run()
    assert at.error and len(at.session_state['deck_draft']['cards'])==1
    assert not at.exception

def test_fifteen_card_manual_review_and_publish(monkeypatch):
    published=[];reviewed=[]
    def review(self,d):
        from logic import deck_fingerprint
        reviewed.append(d.copy());return {'id':'r','fingerprint':deck_fingerprint(d)}
    def publish(self,d,r):
        published.append(d.copy());return {'id':'saved'}
    monkeypatch.setattr('db.DeckRepository.review',review)
    monkeypatch.setattr('db.DeckRepository.publish',publish)
    monkeypatch.setattr('db.DeckRepository.get',lambda self,id:{**published[-1],'profiles':{'username':'student_a'}})
    at=deck_app(monkeypatch);button(at,'+ Create New Deck').click().run()
    next(w for w in at.text_input if w.label=='Deck name').set_value('Finance foundations')
    for i in range(15):
        at.text_area[0].set_value(f'Question {i+1}?')
        for n in range(4):next(w for w in at.text_input if w.label==f'Answer {n+1}').set_value(f'Answer {i+1}.{n+1}')
        ids=[a['id'] for a in at.session_state['deck_draft']['cards'][i]['answers']]
        at.radio[0].set_value(ids[i%4])
        if i<14:button(at,'+ Add Flashcard').click().run()
        else:at.run()
        assert not at.exception
    assert button(at,'+ Add Flashcard').disabled
    assert not button(at,'Save Deck').disabled
    button(at,'Save Deck').click().run()
    assert len(reviewed)==1 and not published
    assert len(at.success)==15
    button(at,'Back to editing').click().run()
    assert at.session_state.get('deck_review') is None
    assert len(at.session_state['deck_draft']['cards'])==15
    button(at,'Save Deck').click().run();button(at,'Create Deck').click().run()
    assert len(published)==1
    assert len(published[0]['cards'])==15
    assert not any(b.label in ('Delete this card','Save Deck') for b in at.button)
    assert not at.exception
