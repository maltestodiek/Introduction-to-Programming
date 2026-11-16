from copy import deepcopy
from logic import scratch_note
from test_deck_ui import button
from test_study_ui import setup as study_setup
from test_play_ui import setup as play_setup,EMPTY


def notes(at):return next(w for w in at.text_area if w.label=='Notes')


def test_scratch_note_keeps_at_most_500_characters():
    assert scratch_note('abc')=='abc'
    assert scratch_note('x'*500)=='x'*500
    assert scratch_note('x'*501)=='x'*500
    assert scratch_note(None)==''


def test_notepad_is_unsaved_scratch_space_and_empty_for_repeated_question(monkeypatch):
    at,calls,d=study_setup(monkeypatch)
    button(at,'Start studying').click().run()
    assert not any(b.label in ('Calculator','Close calculator') for b in at.button)
    assert not any(w.label=='Notes' for w in at.text_area)
    button(at,'Notepad').click().run()
    assert button(at,'Close notepad')
    assert notes(at).proto.max_chars==500
    notes(at).set_value('WACC = E/V * Re + D/V * Rd').run()
    assert not any(a=='answer' for a,_ in calls)
    button(at,'Close notepad').click().run()
    assert not any(w.label=='Notes' for w in at.text_area)
    button(at,'Notepad').click().run()
    assert notes(at).value=='WACC = E/V * Re + D/V * Rd'
    notes(at).set_value('y'*600).run()
    button(at,'Close notepad').click().run();button(at,'Notepad').click().run()
    assert notes(at).value=='y'*500
    assert not any('y'*20 in repr(v) or 'WACC' in repr(v) for _,v in calls)
    button(at,d['cards'][0]['answers'][0]['text']).click().run()
    assert any(a=='answer' for a,_ in calls)
    assert not any('y'*20 in repr(v) for _,v in calls)
    calls.clear();at.run()
    assert button(at,'Notepad')
    assert not any(w.label=='Notes' for w in at.text_area)
    button(at,'Notepad').click().run()
    assert notes(at).value==''
    assert not at.exception


def test_notepad_opens_together_with_calculator(monkeypatch):
    at,calls,d=study_setup(monkeypatch)
    d['cards'][0]['allow_calculator']=True
    button(at,'Start studying').click().run()
    button(at,'Calculator').click().run();button(at,'Notepad').click().run()
    assert button(at,'Close calculator') and button(at,'Close notepad')
    notes(at).set_value('carry the 2').run()
    next(w for w in at.text_input if w.label=='Calculation').set_value('2+2').run()
    button(at,'=').click().run()
    assert at.session_state['calculator_study_session_0_result']=='4'
    assert notes(at).value=='carry the 2'
    assert not any(a=='answer' for a,_ in calls)
    assert not at.exception


def test_notepad_in_classic_duel_round_is_cleared_by_answering(monkeypatch):
    at,calls=play_setup(monkeypatch)
    answered=[]
    def action(self,kind,data=None):
        calls.append((kind,data))
        if kind=='round':return {'state':'question','index':len(answered),'seconds':28,'question':'Which answer?','options':[{'id':str(i),'text':f'Choice {i}'} for i in range(4)]}
        if kind=='answer':answered.append(data);return {'state':'question'}
        return deepcopy(EMPTY)
    monkeypatch.setattr('db.PlayRepository.action',action)
    at.session_state['play_duel']='duel1';at.run()
    button(at,'Notepad').click().run()
    notes(at).set_value('maybe choice 2').run()
    button(at,'Choice 0').click().run()
    assert answered and 'maybe' not in repr(calls)
    assert not any(w.label=='Notes' for w in at.text_area)
    button(at,'Notepad').click().run()
    assert notes(at).value==''
    assert not at.exception
