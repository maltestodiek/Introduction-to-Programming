from copy import deepcopy

import pytest

from logic import deck_studio_created_text, deck_studio_groups, format_deck_time
from test_deck_rules import complete_deck
from test_deck_ui import button, deck_app

DECKS=[
    {'kind':'study','id':'study-private','name':'MarketAnomalies_CF questions','course':'Corporate Finance','language':'English','count':18,'revision':1,
     'created_at':'2026-11-19T19:20:00+00:00','updated_at':'2026-11-19T19:25:38.948911+00:00','published_at':None},
    {'kind':'battle','id':'battle-1','name':'Market efficience questions','course':'Corporate Finance','language':'English','count':15,
     'created_at':'2026-11-19T18:41:00+00:00','source_deck_id':'study-public'},
    {'kind':'study','id':'study-public','name':'Market efficience questions','course':'Corporate Finance','language':'English','count':25,'revision':3,
     'created_at':None,'updated_at':'2026-11-18T10:00:00+00:00','published_at':'2026-11-18T11:00:00+00:00'},
]


def test_times_are_shown_in_the_viewers_time_zone():
    assert format_deck_time('2026-11-19T19:25:38.948911+00:00','Europe/Berlin')=='19 Nov 2026, 20:25'
    assert format_deck_time('2026-11-19T19:25:38Z','America/New_York')=='19 Nov 2026, 14:25'
    assert format_deck_time(None,'Europe/Berlin') is None


def test_unknown_creation_time_is_not_invented():
    assert deck_studio_created_text(DECKS[0],'Europe/Berlin')=='19 Nov 2026, 20:20'
    assert deck_studio_created_text(DECKS[2],'Europe/Berlin')=='On or before 18 Nov 2026'


def test_groups_split_private_published_and_battle_decks():
    groups=deck_studio_groups(DECKS)
    assert [deck['id'] for deck in groups['All']]==['study-private','battle-1','study-public']
    assert [deck['id'] for deck in groups['Private']]==['study-private']
    assert [deck['id'] for deck in groups['Published']]==['study-public']
    assert [deck['id'] for deck in groups['Battle']]==['battle-1']


def studio_app(monkeypatch,calls):
    deck=complete_deck();deck.update(id='study-private',author='Student',revision=1,legacy=False)
    for card in deck['cards']:card.update(chapter='Lecture 1',level=None,note='',feedback=[])
    monkeypatch.setattr('db.StudyRepository.studio',lambda self:deepcopy(DECKS))
    def study(self,action,data=None):
        calls.append(('study',action,data))
        return deepcopy(deck) if action=='deck' else {'decks':[],'shared':[]}
    monkeypatch.setattr('db.StudyRepository.action',study)
    def publication(self,action,data=None):
        calls.append(('publication',action,data))
        return {'decks':[],'published_ids':[]} if action=='list' else {'id':data['id']}
    monkeypatch.setattr('db.StudyRepository.publication',publication)
    def battle(self,kind,data=None):
        if kind=='sources':return {'sources':[{'id':'study-private','name':deck['name'],'course':'Finance','language':'English','count':15,'battle_capable':True}]}
        if kind=='source':return {'name':deck['name'],'cards':[{'id':card['id'],'question':card['question']} for card in deck['cards']]}
        raise AssertionError(kind)
    monkeypatch.setattr('db.BattleRepository.action',battle)
    monkeypatch.setattr('db.BattleRepository.catalog',lambda self:[])
    at=deck_app(monkeypatch)
    button(at,'Open Deck studio').click().run()
    return at


def row_titles(at):
    return [item.value for item in at.markdown if item.value.startswith('**') and 'questions' in item.value]


def test_deck_studio_lists_own_decks_with_status_and_times(monkeypatch):
    at=studio_app(monkeypatch,[])
    assert any(item.value=='Deck studio' for item in at.header)
    text=' '.join([item.value for item in at.markdown]+[item.value for item in at.caption])
    assert 'MarketAnomalies_CF questions' in text and 'Private' in text
    assert 'Published since 18 Nov 2026, 12:00' in text
    assert 'Created 19 Nov 2026, 20:20' in text and 'Last edited 19 Nov 2026, 20:25' in text
    assert 'Created on or before 18 Nov 2026' in text
    assert not at.exception


def test_private_filter_and_publish_action(monkeypatch):
    calls=[]
    at=studio_app(monkeypatch,calls)
    at.segmented_control(key='deck_studio_filter').set_value('Private').run()
    text=' '.join(item.value for item in at.markdown)
    assert 'MarketAnomalies_CF questions' in text and '25 questions' not in text
    at.button(key='studio_publish_study-private').click().run()
    assert ('publication','publish',{'id':'study-private'}) in calls


def test_unpublish_and_edit_actions(monkeypatch):
    calls=[]
    at=studio_app(monkeypatch,calls)
    at.button(key='studio_unpublish_study-public').click().run()
    assert ('publication','unpublish',{'id':'study-public'}) in calls
    at.button(key='studio_edit_study-private').click().run()
    assert at.session_state['study_draft']['id']=='study-private'
    assert at.session_state['study_library'] is True
    assert 'deck_studio' not in at.session_state


def test_battle_action_preselects_the_deck_and_returns_to_the_studio(monkeypatch):
    at=studio_app(monkeypatch,[])
    at.button(key='studio_battle_study-private').click().run()
    assert next(field for field in at.selectbox if field.label=='Source Study deck').value=='study-private'
    button(at,'Back to Deck studio').click().run()
    assert any(item.value=='Deck studio' for item in at.header)
    button(at,'Back to Decks').click().run()
    assert 'deck_studio' not in at.session_state


def test_decks_page_shows_a_large_deck_studio_entry_between_creation_and_courses(monkeypatch):
    monkeypatch.setattr('db.StudyRepository.publication',lambda self,action,data=None:{'decks':[],'published_ids':[]})
    monkeypatch.setattr('db.BattleRepository.catalog',lambda self:[])
    at=deck_app(monkeypatch)
    blocks=[item.value for item in at.markdown]+[item.value for item in at.caption]+[item.value for item in at.subheader]
    studio=blocks.index('#### Deck studio')
    assert any(text.startswith('Edit, publish and track') for text in blocks)
    assert [item.label for item in at.button].count('Open Deck studio')==1
    assert 'Deck studio' not in [item.label for item in at.button]
    assert blocks.index('Your courses')>studio
    assert not at.exception
