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
        if a=='friend_options':return {'friends':[]}
        if a in ('start','review_deck','save_deck'):return {'id':'session'}
        if a=='round':
            answered=any(k=='answer' for k,_ in calls)
            if answered:return {'state':'feedback','index':0,'total':10,'card':d['cards'][0],'correct':True,'answer_id':d['cards'][0]['correct_answer_id']}
            return {'state':'question','index':0,'total':10,'question':d['cards'][0]['question'],'chapter':'Lecture 1','options':d['cards'][0]['answers'],'part':'Solo study','allow_calculator':d['cards'][0].get('allow_calculator',False)}
        return {}
    monkeypatch.setattr('db.StudyRepository.action',action)
    at=deck_app(monkeypatch);button(at,'Play').click().run();button(at,'Study Mode').click().run();button(at,'Study alone').click().run()
    return at,calls,d


def test_solo_filters_start_immediate_locked_feedback_and_explicit_next(monkeypatch):
    at,calls,d=setup(monkeypatch)
    assert not at.exception
    assert any(p.proto.popover.label.strip()=='' for p in at.get('popover'))
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
    button(at,'Change study mode').click().run();button(at,'Study Mode').click().run();button(at,'Study together').click().run()
    assert button(at,'Start studying').disabled
    assert any('20 questions = 10 from your deck + 10' in w.value for w in at.info)
    next(w for w in at.checkbox if w.label.startswith('I agree')).check().run()
    assert not button(at,'Start studying').disabled
    next(w for w in at.selectbox if w.label=='Total questions').set_value(100).run()
    assert button(at,'Start studying').disabled
    assert any('50' in w.value for w in at.warning)
    assert any('100 questions = 50 from your deck + 50' in w.value for w in at.info)
    assert not at.exception


def test_study_editor_requires_review_and_adds_more_questions(monkeypatch):
    at,calls,d=setup(monkeypatch)
    button(at,'Decks').click().run();button(at,'Study decks & progress').click().run();button(at,'Create Study deck').click().run()
    button(at,'Add Study question').click().run();assert at.error
    for label,value in [('Study deck name','Practice'),('Question','A question?')]+[(f'Answer {i}',f'Choice {i}') for i in range(1,5)]:
        next(w for w in at.text_input if w.label==label).set_value(value)
    next(w for w in at.selectbox if w.label=='Subsection / lecture').set_value('Lecture 1')
    card=at.session_state.study_draft['cards'][0]
    next(w for w in at.radio if w.label=='Correct answer').set_value(card['answers'][0]['id'])
    button(at,'Review Study deck').click().run()
    assert any(a=='review_deck' for a,_ in calls)
    assert not any(a=='save_deck' for a,_ in calls)
    button(at,'Back to Study editing').click().run();button(at,'Add Study question').click().run()
    assert len(at.session_state.study_draft['cards'])==2
    assert not at.exception


def test_friend_settings_only_request_eligible_friends(monkeypatch):
    at,calls,d=setup(monkeypatch)
    button(at,'Change study mode').click().run();button(at,'Study Mode').click().run();button(at,'Study together').click().run();button(at,'Friend').click().run()
    assert ('friend_options',{'deck_id':d['id']}) in calls
    assert not any('Invite even' in w.label for w in at.checkbox)
    assert any('don’t have any friends yet' in w.value for w in at.info)
    assert button(at,'Go to Friends')
    assert not at.exception


def test_incoming_invites_visible_before_course_setup(monkeypatch):
    import db
    at,calls,d=setup(monkeypatch)
    original=db.StudyRepository.action
    def with_invite(self,action,data=None):
        result=original(self,action,data)
        if action=='list':result['invites']=[{'id':'invite','username':'Alex','course':'Math','language':'English','count':40}]
        return result
    monkeypatch.setattr('db.StudyRepository.action',with_invite)
    at.run()
    assert button(at,'Accept invitation')
    assert any('Math' in w.value and '40 questions' in w.value for w in at.caption)
    button(at,'Accept invitation').click().run()
    assert any('compatible deck' in w.value for w in at.warning)
    assert not any('Accept an invitation or invite'==w.label for w in at.selectbox)
    assert not at.exception


def test_study_choices_require_click_each_time_play_menu_opens(monkeypatch):
    at,calls,d=setup(monkeypatch)
    button(at,'Change study mode').click().run()
    assert button(at,'Study Mode')
    assert not any(b.label in ('Study alone','Study together') for b in at.button)
    button(at,'Study Mode').click().run()
    assert button(at,'Study alone') and button(at,'Study together')
    button(at,'Play').click().run()
    assert button(at,'Study Mode')
    assert not any(b.label in ('Study alone','Study together') for b in at.button)
    assert not at.exception


def test_calculator_only_for_enabled_question_and_does_not_submit_answer(monkeypatch):
    at,calls,d=setup(monkeypatch)
    d['cards'][0]['allow_calculator']=True
    button(at,'Start studying').click().run()
    button(at,'Calculator').click().run()
    assert button(at,'Close calculator')
    next(w for w in at.text_input if w.label=='Calculation').set_value('(10+5)/3').run()
    button(at,'=').click().run()
    assert next(w for w in at.text_input if w.label=='Calculation').value=='(10+5)/3'
    assert at.session_state['calculator_study_session_0_result']=='5'
    next(w for w in at.text_input if w.label=='Calculation').set_value('sqrt(81)+2^3').run()
    button(at,'=').click().run()
    assert at.session_state['calculator_study_session_0_result']=='17'
    assert not any(a=='answer' for a,_ in calls)
    button(at,'C').click().run()
    assert next(w for w in at.text_input if w.label=='Calculation').value==''
    d['cards'][0]['allow_calculator']=False
    at.run()
    assert not any(b.label in ('Calculator','Close calculator') for b in at.button)
    assert not at.exception


def test_main_creation_supports_more_than_fifteen_and_reuses_subsections(monkeypatch):
    at,calls,d=setup(monkeypatch)
    button(at,'Decks').click().run();button(at,'+ Create New Deck').click().run()
    assert 'study_draft' in at.session_state
    draft=complete_deck()
    for card in draft['cards']:card['chapter']='Lecture 1'
    at.session_state['study_draft']=draft
    at.run()
    button(at,'Add Study question').click().run()
    assert len(at.session_state.study_draft['cards'])==16
    assert at.session_state.study_draft['cards'][-1]['chapter']=='Lecture 1'
    assert next(w for w in at.selectbox if w.label=='Subsection / lecture').value=='Lecture 1'
    section=next(w for w in at.selectbox if w.label=='Subsection / lecture')
    # AppTest cannot serialize a newly typed option yet; mirror the browser's new-option entry.
    section.options.append('Lecture 2')
    section.set_value('Lecture 2').run()
    assert at.session_state.study_draft['cards'][-1]['chapter']=='Lecture 2'
    next(w for w in at.checkbox if w.label=='Allow calculator for this question').check().run()
    assert at.session_state.study_draft['cards'][-1]['allow_calculator'] is True
    assert not at.exception


def test_play_lists_active_study_below_creation_and_resumes(monkeypatch):
    import db
    at,calls,d=setup(monkeypatch)
    original=db.StudyRepository.action
    def ongoing(self,action,data=None):
        result=original(self,action,data)
        if action=='list':result['sessions']=[{'id':'active','name':'Saved finance','mode':'solo','state':'own','count':20,'cursor':4},{'id':'finished','name':'Finished finance','mode':'solo','state':'completed','count':10,'cursor':10}]
        return result
    monkeypatch.setattr('db.StudyRepository.action',ongoing)
    button(at,'Play').click().run()
    headings=[w.value for w in at.subheader]
    assert headings.index('Create new session')<headings.index('Ongoing sessions')
    assert any('Saved finance' in w.value for w in at.markdown)
    assert not any('Finished finance' in w.value for w in at.markdown)
    button(at,'Resume Study').click().run()
    assert ('round',{'id':'active'}) in calls
    assert at.session_state.study_session=='active'
    button(at,'Play').click().run();button(at,'Study Mode').click().run();button(at,'Study alone').click().run()
    assert button(at,'Start studying')
    assert 'study_session' not in at.session_state
    assert not at.exception


def test_colour_dropdown_keeps_combined_learning_levels(monkeypatch):
    at,calls,d=setup(monkeypatch)
    for label in ['Building confidence','Getting stronger','Well practised']:
        next(w for w in at.checkbox if w.label==label).uncheck()
    at.run()
    button(at,'Start studying').click().run()
    assert any(action=='start' and data['levels']==['new','0'] for action,data in calls)
    assert not at.exception
