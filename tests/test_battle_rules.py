from copy import deepcopy

import pytest

from logic import battle_creator_reward, battle_rating_score, select_battle_cards
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


def test_creator_reward_only_applies_to_one_good_human_rating():
    assert battle_creator_reward('good', source_origin='human', creator_is_player=False) == 5
    assert battle_creator_reward('neutral', source_origin='human', creator_is_player=False) == 0
    assert battle_creator_reward('bad', source_origin='human', creator_is_player=False) == 0
    assert battle_creator_reward('good', source_origin='ai', creator_is_player=False) == 0
    assert battle_creator_reward('good', source_origin='chatbot', creator_is_player=False) == 0
    assert battle_creator_reward('good', source_origin='human', creator_is_player=True) == 0
