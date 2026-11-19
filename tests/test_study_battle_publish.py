from copy import deepcopy

from test_deck_rules import complete_deck
from test_deck_ui import button, deck_app

LABEL='Publish as Battle deck'


def study_deck_page(monkeypatch,card_count=15,shared=False):
    d=complete_deck();d.update(author='Student',revision=1,legacy=False)
    d['cards']=d['cards'][:card_count]
    for c in d['cards']:c.update(chapter='Lecture 1',level=None,note='',feedback=[])
    monkeypatch.setattr('db.StudyRepository.action',lambda self,a,data=None:deepcopy(d) if a=='deck' else {})
    def battle(self,kind,data=None):
        if kind=='sources':return {'sources':[
            {'id':'other-deck','name':'Other','course':'Finance','language':'English','count':20,'battle_capable':True},
            {'id':d['id'],'name':d['name'],'course':'Finance','language':'English','count':card_count,'battle_capable':card_count>=15},
        ]}
        if kind=='source':return {'name':d['name'],'cards':[{'id':c['id'],'question':c['question']} for c in d['cards']]}
        raise AssertionError(kind)
    monkeypatch.setattr('db.BattleRepository.action',battle)
    at=deck_app(monkeypatch)
    at.session_state['study_library']=True
    at.session_state['study_deck_open']={'id':d['id'],'shared':shared}
    at.run()
    return at,d


def test_own_study_deck_opens_the_battle_creator_with_this_deck_selected(monkeypatch):
    at,d=study_deck_page(monkeypatch)
    publish=button(at,LABEL)
    assert not publish.disabled
    publish.click().run()
    assert any(item.value=='Create Battle Mode Deck' for item in at.header)
    assert next(field for field in at.selectbox if field.label=='Source Study deck').value==d['id']
    assert len(at.checkbox)==16  # 15 questions plus the public-play confirmation.
    button(at,'Back to Study deck').click().run()
    assert 'battle_deck_creator' not in at.session_state
    assert any(item.value==d['name'] for item in at.subheader)
    assert not at.exception


def test_study_deck_with_fewer_than_fifteen_questions_cannot_be_published_for_battle(monkeypatch):
    at,_=study_deck_page(monkeypatch,card_count=12)
    assert button(at,LABEL).disabled
    assert any('at least 15 questions' in item.value for item in at.caption)


def test_shared_study_copy_offers_no_battle_publishing(monkeypatch):
    at,_=study_deck_page(monkeypatch,shared=True)
    assert not any(item.label==LABEL for item in at.button)
