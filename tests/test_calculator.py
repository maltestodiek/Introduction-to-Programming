import pytest
from logic import calculate, validate_card, validate_study_deck
from test_deck_rules import complete_deck


@pytest.mark.parametrize('expression, expected', [('2+3*4','14'),('(2+3)*4','20'),('0.1+0.2','0.3'),('-8/2','-4'),('12.5 × 2 ÷ 5','5'),('2^3','8'),('sqrt(81)','9'),('sqrt(9)+2^3','11'),('2^-2','0.25')])
def test_basic_calculations(expression, expected):
    assert calculate(expression)==expected


@pytest.mark.parametrize('expression, expected', [('1/3','0.3333'),('2/3','0.6667'),('10/4','2.5'),('sqrt(2)','1.4142'),('1000000/7','142857.1429'),('0.0045','0.0045'),('0.00005','0.0001'),('1.00005','1.0001'),('-0.00005','-0.0001'),('2.67895','2.679'),('0.00004','0'),('-0.00001','0'),('2^-12','0.0002'),('4.0000','4')])
def test_results_are_rounded_to_four_decimal_places(expression, expected):
    assert calculate(expression)==expected


def test_rounding_happens_only_at_the_end():
    assert calculate('(1/3)*3')=='1'
    assert calculate('0.00004+0.00004')=='0.0001'


def test_calculator_tells_the_user_that_results_are_rounded(monkeypatch):
    from test_deck_ui import button
    from test_study_ui import setup
    at,calls,d=setup(monkeypatch)
    d['cards'][0]['allow_calculator']=True
    button(at,'Start studying').click().run()
    button(at,'Calculator').click().run()
    assert any('Rounded to 4 decimal places' in element.proto.body for element in at.get('html'))
    next(w for w in at.text_input if w.label=='Calculation').set_value('1/3').run()
    button(at,'=').click().run()
    assert at.session_state['calculator_study_session_0_result']=='0.3333'
    assert not at.exception


@pytest.mark.parametrize('expression', ['1/0','sqrt(-1)','sqrt(1,2)','2**100','abs(-1)','__import__("os")','1<<2','[1]','True+1','', '9'*121])
def test_invalid_calculations_are_rejected(expression):
    with pytest.raises(ValueError):calculate(expression)


def test_question_permission_defaults_off_and_survives_validation():
    d=complete_deck();c=d['cards'][0]
    assert validate_card(c)['allow_calculator'] is False
    c['allow_calculator']=True
    assert validate_study_deck(d)['cards'][0]['allow_calculator'] is True
    c['allow_calculator']='yes'
    with pytest.raises(ValueError):validate_card(c)
