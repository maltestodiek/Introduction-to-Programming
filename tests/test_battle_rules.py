from copy import deepcopy
from datetime import datetime,timezone

import pytest

from logic import battle_rating_score, battle_search_remaining_seconds, battle_search_timer_text, battle_session_groups, recent_completed_battles, select_battle_cards
from test_deck_rules import complete_deck


def test_battle_snapshot_requires_exactly_fifteen_distinct_valid_cards():
    source = complete_deck()
    snapshot = select_battle_cards(source, [card['id'] for card in source['cards']], consent=True)
    assert len(snapshot) == 15
    assert [card['id'] for card in snapshot] == [card['id'] for card in source['cards']]

    with pytest.raises(ValueError, match='15'):
        select_battle_cards(source, [card['id'] for card in source['cards'][:14]], consent=True)
    with pytest.raises(ValueError, match='distinct'):
        select_battle_cards(source, [source['cards'][0]['id']] * 15, consent=True)
    with pytest.raises(ValueError, match='accept'):
        select_battle_cards(source, [card['id'] for card in source['cards']], consent=False)


def test_battle_snapshot_is_a_copy_not_a_live_study_deck_reference():
    source = complete_deck()
    chosen = [card['id'] for card in source['cards']]
    snapshot = select_battle_cards(source, chosen, consent=True)
    source['cards'][0]['question'] = 'Edited after submission'
    assert snapshot[0]['question'] != source['cards'][0]['question']


@pytest.mark.parametrize('rating, expected', [('good', 1), ('neutral', 0), ('bad', -1)])
def test_battle_rating_score_uses_three_level_traffic_light(rating, expected):
    assert battle_rating_score(rating) == expected


def test_battle_session_groups_use_new_battle_mode_status_values():
    groups = battle_session_groups([
        {'id': 'ongoing', 'status': 'ongoing'},
        {'id': 'pending', 'status': 'pending'},
        {'id': 'completed', 'status': 'completed'},
    ])
    assert [session['id'] for session in groups['ongoing']] == ['ongoing', 'pending']
    assert [session['id'] for session in groups['completed']] == ['completed']


def test_recent_completed_battles_shows_only_the_three_newest_saved_results():
    sessions=[{'id':str(index),'status':'completed'} for index in range(4)]+[{'id':'open','status':'ongoing'}]
    assert [session['id'] for session in recent_completed_battles(sessions)]==['0','1','2']


def test_pending_battle_search_timer_counts_down_and_stops_at_zero():
    now=datetime(2026,11,19,12,0,0,tzinfo=timezone.utc)
    assert battle_search_remaining_seconds('2026-11-19T13:00:00Z',now)==3600
    assert battle_search_timer_text(3599)=='00:59:59'
    assert battle_search_remaining_seconds('2026-11-19T11:59:59Z',now)==0
