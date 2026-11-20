from pathlib import Path
from unittest.mock import Mock

from streamlit.testing.v1 import AppTest

from auth import AuthService
from logic import DEFAULT_AVATAR
from test_deck_ui import Obj


BATTLE_OVERVIEW_CSS=(Path(__file__).parents[1]/'assets'/'battle-overview.css').read_text()

BATTLE=[
    {'id':'battle-own','name':'Market efficiency Battle','course':'Corporate Finance','language':'English','author':'student_a','count':15,'owned':True},
    {'id':'battle-other','name':'Bonds Battle','course':'Corporate Finance','language':'English','author':'student_b','count':15,'owned':False},
]


def overview(monkeypatch,catalog=BATTLE,failure=None):
    profile={'username':'student_a','university':'Example University','courses':['Corporate Finance','Investments'],'languages':['English'],'avatar':DEFAULT_AVATAR,'image_mode':'Avatar'}
    monkeypatch.setattr('db.ProfileRepository.load',lambda self:profile)
    monkeypatch.setattr('db.DeckRepository.list',lambda self,course:[{'id':'legacy-1','name':'Old classic duel deck','course':course,'language':'English','creator_id':'a','profiles':{'username':'student_a'}}])
    def battle_catalog(self):
        if failure:raise ValueError(failure)
        return catalog
    monkeypatch.setattr('db.BattleRepository.catalog',battle_catalog)
    monkeypatch.setattr('db.StudyRepository.publication',lambda self,action,data=None:{'decks':[
        {'id':'study-1','name':'WACC basics','course':'Corporate Finance','language':'English','author':'student_a','count':20,'owned':True},
    ]} if action=='list' else {})
    client=Mock();client.auth.get_user.return_value=Obj(user=Obj(id='a'))
    auth=AuthService(client);auth.user=client.auth.get_user.return_value.user
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=20)
    at.session_state['auth']=auth;at.session_state['main_page']='Decks';at.run()
    return at


def deck_titles(at):
    return [item.value for item in at.markdown if item.value.startswith('#### ')]


def test_browse_decks_filters_published_battle_decks(monkeypatch):
    at=overview(monkeypatch)
    at.segmented_control(key='deck_library_filter').set_value('Battle').run()
    titles=deck_titles(at)
    assert '#### Market efficiency Battle' in titles and '#### Bonds Battle' in titles
    assert '#### WACC basics' not in titles
    assert '#### Old classic duel deck' not in titles
    assert not at.exception


def test_created_by_me_filter_includes_own_battle_decks_only(monkeypatch):
    at=overview(monkeypatch)
    at.segmented_control(key='deck_library_filter').set_value('Created by me').run()
    titles=deck_titles(at)
    assert '#### Market efficiency Battle' in titles and '#### WACC basics' in titles
    assert '#### Bonds Battle' not in titles


def test_browse_decks_searches_by_deck_name(monkeypatch):
    at=overview(monkeypatch)
    at.text_input(key='deck_library_search').set_value('Bonds').run()
    titles=deck_titles(at)
    assert '#### Bonds Battle' in titles
    assert '#### Market efficiency Battle' not in titles
    assert '#### WACC basics' not in titles
    assert not at.exception


def test_course_card_counts_battle_decks_from_the_catalogue(monkeypatch):
    at=overview(monkeypatch)
    counts=[item.value for item in at.markdown if 'course-list-count' in item.value]
    assert '<strong>1</strong><span>Study decks</span><strong>2</strong><span>Battle decks</span>' in counts[0]
    assert '<strong>0</strong><span>Study decks</span><strong>0</strong><span>Battle decks</span>' in counts[1]


def test_deck_catalogue_never_offers_a_direct_battle_start(monkeypatch):
    at=overview(monkeypatch)
    labels=[item.label for item in at.button]
    assert 'Start Battle' not in labels
    assert 'Battle' not in labels
    assert labels.count('Study')==2
    assert not any('Start Battles from the Play menu.' in item.value for item in at.caption)
    assert not at.exception


def test_unavailable_battle_catalogue_keeps_study_decks_visible(monkeypatch):
    at=overview(monkeypatch,failure='Battle decks could not be loaded. Refresh and retry.')
    assert any('Battle decks could not be loaded' in item.value for item in at.warning)
    assert '#### WACC basics' in deck_titles(at)
    assert not at.exception


def test_battle_dashboard_hero_uses_compact_even_vertical_spacing():
    assert 'padding:22px 28px!important' in BATTLE_OVERVIEW_CSS
    assert 'margin:0 0 .45rem!important' in BATTLE_OVERVIEW_CSS
    assert 'margin:0!important' in BATTLE_OVERVIEW_CSS
    assert 'margin-top:14px;margin-bottom:0' in BATTLE_OVERVIEW_CSS
