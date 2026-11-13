import pytest
from logic import calculate, validate_card, validate_study_deck
from test_deck_rules import complete_deck


@pytest.mark.parametrize('expression, expected', [('2+3*4','14'),('(2+3)*4','20'),('0.1+0.2','0.3'),('-8/2','-4'),('12.5 × 2 ÷ 5','5')])
def test_basic_calculations(expression, expected):
    assert calculate(expression)==expected


@pytest.mark.parametrize('expression', ['1/0','2**100','abs(-1)','__import__("os")','1<<2','[1]','True+1','', '9'*121])
def test_invalid_calculations_are_rejected(expression):
    with pytest.raises(ValueError):calculate(expression)


def test_question_permission_defaults_off_and_survives_validation():
    d=complete_deck();c=d['cards'][0]
    assert validate_card(c)['allow_calculator'] is False
    c['allow_calculator']=True
    assert validate_study_deck(d)['cards'][0]['allow_calculator'] is True
    c['allow_calculator']='yes'
    with pytest.raises(ValueError):validate_card(c)
