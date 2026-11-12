from copy import deepcopy
import pytest
from test_deck_rules import complete_deck
from logic import validate_study_deck, study_level, study_card_version, filter_study_cards


def test_variable_decks_and_chapters():
    d=complete_deck();d['cards']=d['cards'][:1];d['cards'][0]['chapter']='Lecture 1'
    assert validate_study_deck(d)['cards'][0]['chapter']=='Lecture 1'
    d['cards']=[]
    with pytest.raises(ValueError):validate_study_deck(d)


def test_progress_steps_and_wrong_first():
    assert study_level(None,False)==0
    assert study_level(None,True)==1
    assert [study_level(i,True) for i in range(4)]==[1,2,3,3]
    assert [study_level(i,False) for i in range(4)]==[0,0,1,2]


def test_question_edit_resets_identity_but_chapter_does_not():
    c=complete_deck()['cards'][0];v=study_card_version(c)
    c['chapter']='Lecture 2';assert study_card_version(c)==v
    c['question']='New meaning';assert study_card_version(c)!=v


def test_filters_intersect_chapters_and_multiple_levels():
    cards=complete_deck()['cards'][:3]
    for i,c in enumerate(cards):c.update(chapter='A' if i<2 else 'B',level=None if i==0 else i)
    assert filter_study_cards(cards,['A'],['new','1'])==cards[:2]
    assert filter_study_cards(cards,['B'],['new','1'])==[]
    assert filter_study_cards(cards,[],['new','2'])==[cards[0],cards[2]]


def test_validation_preserves_input_and_rejects_duplicate_ids():
    d=complete_deck();before=deepcopy(d);validate_study_deck(d);assert d==before
    d['cards'].append(deepcopy(d['cards'][0]))
    with pytest.raises(ValueError):validate_study_deck(d)
