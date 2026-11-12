from copy import deepcopy
from test_deck_ui import deck_app,button
from test_deck_rules import complete_deck


def setup(monkeypatch):
    calls=[];d=complete_deck();d.update(author='Student',revision=1,legacy=False)
    for c in d['cards']:c.update(chapter='Lecture 1',level=None,note='',feedback=[])
    state={'decks':[{'id':d['id'],'name':d['name'],'course':'Finance','language':'English','count':15,'revision':1,'legacy':False}],'shared':[],'sessions':[],'open':[],'invites':[],'friends':[],'feedback':[]}
    def action(self,a,data=None):
        calls.append((a,data))
        if a=='list':return deepcopy(state)
        if a=='deck':return deepcopy(d)
        if a in ('start','review_deck','save_deck'):return {'id':'session'}
        if a=='round':
            answered=any(k=='answer' for k,_ in calls)
            if answered:return {'state':'feedback','index':0,'total':10,'card':d['cards'][0],'correct':True,'answer_id':d['cards'][0]['correct_answer_id']}
            return {'state':'question','index':0,'total':10,'question':d['cards'][0]['question'],'chapter':'Lecture 1','options':d['cards'][0]['answers'],'part':'Solo study'}
        return {}
    monkeypatch.setattr('db.StudyRepository.action',action)
    at=deck_app(monkeypatch);button(at,'Play').click().run();button(at,'Study Mode').click().run()
    return at,calls,d


def test_solo_filters_start_immediate_locked_feedback_and_explicit_next(monkeypatch):
    at,calls,d=setup(monkeypatch)
    assert not at.exception
    button(at,'Start studying').click().run()
    assert any(a=='start' and v['count']==10 and v['mode']=='solo' for a,v in calls)
    button(at,d['cards'][0]['answers'][0]['text']).click().run()
    assert any(s.value=='Correct!' for s in at.success)
    assert not any(a=='next' for a,_ in calls)
    assert button(at,'Next question')
    assert not any(b.label==d['cards'][0]['answers'][0]['text'] for b in at.button)
    button(at,'Save private note').click().run()
    assert any(a=='annotate' and 'note' in v and 'feedback' not in v for a,v in calls)
    assert not at.exception


def test_together_requires_consent_and_sufficient_questions(monkeypatch):
    at,calls,d=setup(monkeypatch)
    next(w for w in at.radio if w.label=='How would you like to study?').set_value('Study together').run()
    assert button(at,'Start studying').disabled
    next(w for w in at.checkbox if w.label.startswith('I agree')).check().run()
    assert not button(at,'Start studying').disabled
    next(w for w in at.selectbox if w.label=='Total questions').set_value(100).run()
    assert button(at,'Start studying').disabled
    assert any('50' in w.value for w in at.warning)
    assert not at.exception


def test_study_editor_requires_review_and_adds_more_questions(monkeypatch):
    at,calls,d=setup(monkeypatch)
    button(at,'Decks').click().run();button(at,'Study decks & progress').click().run();button(at,'Create Study deck').click().run()
    button(at,'Add Study question').click().run();assert at.error
    for label,value in [('Study deck name','Practice'),('Question','A question?'),('Chapter / lecture (optional)','Lecture 1')]+[(f'Answer {i}',f'Choice {i}') for i in range(1,5)]:
        next(w for w in at.text_input if w.label==label).set_value(value)
    card=at.session_state.study_draft['cards'][0]
    next(w for w in at.radio if w.label=='Correct answer').set_value(card['answers'][0]['id'])
    button(at,'Review Study deck').click().run()
    assert any(a=='review_deck' for a,_ in calls)
    assert not any(a=='save_deck' for a,_ in calls)
    button(at,'Back to Study editing').click().run();button(at,'Add Study question').click().run()
    assert len(at.session_state.study_draft['cards'])==2
    assert not at.exception
