from copy import deepcopy
import pytest
from logic import new_deck, new_card, validate_card, validate_deck, deck_fingerprint, add_card, delete_card


def complete_deck():
    d=new_deck('Finance');d['name']='Finance foundations'
    d['cards']=[]
    for i in range(15):
        c=new_card();c['question']=f'Question {i+1}?'
        for n,a in enumerate(c['answers']):a['text']=f'Answer {i+1}.{n+1}'
        c['correct_answer_id']=c['answers'][i%4]['id'];d['cards'].append(c)
    return d


def test_complete_deck_retains_all_order_and_solutions():
    d=complete_deck();assert validate_deck(d)==d
    assert len({a['id'] for c in d['cards'] for a in c['answers']})==60

@pytest.mark.parametrize('count',[0,14,16])
def test_exactly_fifteen(count):
    d=complete_deck();d['cards']=(d['cards']+[new_card()])[:count]
    with pytest.raises(ValueError,match='15'):validate_deck(d)

@pytest.mark.parametrize('change',[lambda c:c.update(question=' '),lambda c:c['answers'][3].update(text=' '),lambda c:c.update(answers=c['answers'][:3]),lambda c:c.update(correct_answer_id=None),lambda c:c.update(correct_answer_id='unknown'),lambda c:c.update(correct_answer_id=[c['answers'][0]['id'],c['answers'][1]['id']])])
def test_incomplete_card_rejected_without_mutation(change):
    c=complete_deck()['cards'][0];change(c);before=deepcopy(c)
    with pytest.raises(ValueError):validate_card(c)
    assert c==before

def test_add_rejects_incomplete_and_sixteenth():
    d=new_deck('Finance');before=deepcopy(d)
    with pytest.raises(ValueError):add_card(d)
    assert d==before
    with pytest.raises(ValueError,match='15'):add_card(complete_deck())

def test_delete_middle_preserves_answer_ids_then_replace():
    d=complete_deck();expected=d['cards'][:6]+d['cards'][7:]
    changed=delete_card(d,6)
    assert changed['cards']==expected
    changed=add_card(changed)
    assert len(changed['cards'])==15 and changed['cards'][:14]==expected

def test_review_fingerprint_changes_after_edit():
    d=complete_deck();before=deck_fingerprint(d)
    d['cards'][2]['correct_answer_id']=d['cards'][2]['answers'][0]['id']
    assert deck_fingerprint(d)!=before

@pytest.mark.parametrize('field',['name','course'])
def test_blank_metadata_rejected(field):
    d=complete_deck();d[field]=' '
    with pytest.raises(ValueError):validate_deck(d)
