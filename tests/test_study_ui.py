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
    monkeypatch.setattr('db.StudyRepository.progress',lambda self,session_id:{'answers':[]})
    monkeypatch.setattr('db.StudyRepository.publication',lambda self,a,data=None:{'published_ids':[],'decks':[]} if a=='list' else {'id':data['id']})
    at=deck_app(monkeypatch);button(at,'Play').click().run();button(at,'Study Mode').click().run();button(at,'Study alone').click().run()
    assert not any(b.label=='Start studying' for b in at.button)
    button(at,'Create a new study session').click().run()
    return at,calls,d


def test_solo_filters_start_immediate_locked_feedback_and_explicit_next(monkeypatch):
    at,calls,d=setup(monkeypatch)
    assert not at.exception
    assert button(at,'Back to Study alone')
    assert not any(b.label=='Change study mode' for b in at.button)
    assert any(p.proto.popover.label.strip()=='' for p in at.get('popover'))
    button(at,'Start studying').click().run()
    assert any(a=='start' and v['count']==10 and v['mode']=='solo' for a,v in calls)
    assert not at.exception
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
    button(at,'Back to Study alone').click().run()
    button(at,'Change study mode').click().run();button(at,'Study together').click().run()
    assert not any(b.label=='Start studying' for b in at.button)
    assert any(p.proto.popover.help=='Study Together session rules' for p in at.get('popover'))
    button(at,'Create a new study session').click().run()
    assert button(at,'Back to Study together')
    assert not any(b.label=='Change study mode' for b in at.button)
    assert button(at,'Start studying').disabled
    assert any(p.proto.popover.help=='Study Together session rules' for p in at.get('popover'))
    assert not any('questions = ' in w.value for w in at.info)
    assert any(p.proto.popover.help=='Learning progress legend' for p in at.get('popover'))
    for level in ('new', '0', '1', '2', '3'):
        at.checkbox(key='study_together_levels_'+level).uncheck()
    at.run()
    assert any('Choose at least one preferred learning level' in w.value for w in at.warning)
    at.checkbox(key='study_together_levels_new').check().run()
    next(w for w in at.checkbox if w.label.startswith('I agree')).check().run()
    assert not button(at,'Start studying').disabled
    next(w for w in at.selectbox if w.label=='Total questions').set_value(100).run()
    assert button(at,'Start studying').disabled
    assert any('50' in w.value for w in at.warning)
    from pathlib import Path
    app=(Path(__file__).parents[1]/'app.py').read_text()
    assert "st.markdown('**Game rules**')" in app
    assert 'Both players answer the same combined question set.' in app
    assert not at.exception


def test_study_editor_requires_review_and_adds_more_questions(monkeypatch):
    at,calls,d=setup(monkeypatch)
    at.session_state['main_page']='Decks';at.session_state['study_library']=True;at.run()
    button(at,'Create Study deck').click().run()
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


def test_study_library_can_publish_an_owned_deck(monkeypatch):
    published=[]
    at,calls,d=setup(monkeypatch)
    def publication(self,action,data=None):
        if action=='list':return {'published_ids':published,'decks':[]}
        if action=='publish':published.append(data['id']);return {'id':data['id'],'published':True}
        return {'id':data['id'],'published':False}
    monkeypatch.setattr('db.StudyRepository.publication',publication)
    at.session_state['main_page']='Decks';at.session_state['study_library']=True;at.run()
    button(at,'Publish Study deck').click().run()
    assert d['id'] in published
    assert any('Published to students' in item.value for item in at.caption)
    assert not at.exception


def test_decks_navigation_returns_from_study_library_to_course_decks(monkeypatch):
    at,calls,d=setup(monkeypatch)
    at.session_state['main_page']='Decks';at.session_state['study_library']=True;at.run()
    assert not any(w.label=='Back to course decks' for w in at.button)
    button(at,'Decks').click().run()
    assert not at.session_state.get('study_library')
    assert any(heading.value=='Your courses' for heading in at.subheader)
    assert not at.exception


def test_friend_settings_only_request_eligible_friends(monkeypatch):
    at,calls,d=setup(monkeypatch)
    button(at,'Back to Study alone').click().run()
    button(at,'Change study mode').click().run();button(at,'Study together').click().run();button(at,'Create a new study session').click().run();button(at,'Friend').click().run()
    assert ('friend_options',{'deck_id':d['id'],'count':20}) in calls
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
    button(at,'Back to Study alone').click().run()
    assert 'Study invitations' not in [h.value for h in at.subheader]
    assert not any(b.label in ('Accept invitation', 'Decline') for b in at.button)
    button(at,'Change study mode').click().run()
    assert button(at,'Accept invitation')
    button(at,'Study together').click().run()
    assert button(at,'Accept invitation')
    assert any('Math' in w.value and '40 questions' in w.value for w in at.caption)
    button(at,'Accept invitation').click().run()
    assert any('compatible deck' in w.value for w in at.warning)
    assert not any('Accept an invitation or invite'==w.label for w in at.selectbox)
    assert not at.exception


def test_accepting_an_invitation_locks_the_matched_course_in_the_setup(monkeypatch):
    import db
    at,calls,d=setup(monkeypatch)
    original=db.StudyRepository.action
    def with_compatible_invite(self,action,data=None):
        result=original(self,action,data)
        if action=='list':
            result['invites']=[{'id':'invite','username':'Alex','course':'Finance','language':'English','count':20}]
        return result
    monkeypatch.setattr('db.StudyRepository.action',with_compatible_invite)
    button(at,'Back to Study alone').click().run()
    button(at,'Change study mode').click().run()
    button(at,'Study together').click().run()
    button(at,'Accept invitation').click().run()
    assert any(h.value=='Finance – Study together' for h in at.subheader)
    assert not any(widget.label=='Study course' for widget in at.selectbox)
    assert any('Joining: Finance · English · 20 questions' in item.value for item in at.info)
    assert not any(widget.label in ('Random player', 'Friend') for widget in at.button)
    assert not at.exception


def test_study_choices_require_click_each_time_play_menu_opens(monkeypatch):
    at,calls,d=setup(monkeypatch)
    button(at,'Back to Study alone').click().run()
    for current in ('Study alone', 'Study together'):
        assert at.session_state['study_choice'] == current
        button(at,'Change study mode').click().run()
        assert button(at,'Study alone') and button(at,'Study together')
        assert not any(b.label=='Battle Mode' for b in at.button)
        if current=='Study alone':
            button(at,'Study together').click().run()
    assert not any(b.label=='Change play mode' for b in at.button)
    button(at,'Play').click().run()
    assert button(at,'Study Mode')
    assert not any(b.label in ('Study alone','Study together') for b in at.button)
    assert not at.exception


def test_study_mode_picker_uses_the_same_blue_and_violet_colours_as_session_badges():
    from pathlib import Path
    css=(Path(__file__).parents[1]/'assets'/'study-design.css').read_text()
    assert '.st-key-enter_solo button{background:#eaf3ff!important;border-color:#b9cdf7!important;color:#2554b8!important}' in css
    assert '.st-key-enter_together button{background:#f5edff!important;border-color:#dcc5ff!important;color:#6d32c7!important}' in css


def test_selected_battle_mode_hides_mode_picker_without_a_redundant_change_button(monkeypatch):
    at,calls,d=setup(monkeypatch)
    button(at,'Play').click().run()
    button(at,'Battle Mode').click().run()
    assert not any(w.value=='Create new session' for w in at.subheader)
    assert not any(b.label=='Study Mode' for b in at.button)
    assert not any(button.label=='Change play mode' for button in at.button)
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
    button(at,'Decks').click().run()
    button(at,'Create Study Deck').click().run()
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


def test_play_landing_shows_only_the_two_mode_cards(monkeypatch):
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
    assert 'Create new session' not in headings
    assert headings.count('Battle Mode')==1 and headings.count('Study Mode')==1
    assert not any(name in headings for name in ['Your study sessions','Ongoing study sessions','Study history'])
    assert not any('Saved finance' in w.value or 'Finished finance' in w.value for w in at.markdown)
    assert not any((item.key or '').startswith(('continue_session','home_study_','history_study_')) for item in at.button)
    button(at,'Play').click().run();button(at,'Study Mode').click().run();button(at,'Study alone').click().run()
    button(at,'Create a new study session').click().run()
    assert button(at,'Start studying')
    assert not at.exception


def test_level_cards_keep_combined_learning_levels(monkeypatch):
    at,calls,d=setup(monkeypatch)
    for label in ['Level 1 · Building confidence','Level 2 · Getting stronger','Level 3 · Well practised']:
        next(w for w in at.checkbox if w.label==label).uncheck()
    at.run()
    button(at,'Start studying').click().run()
    assert any(action=='start' and data['levels']==['new','0'] for action,data in calls)
    assert not at.exception


def test_reopening_study_settings_in_a_fresh_app(monkeypatch):
    from types import SimpleNamespace
    from auth import AuthService
    from streamlit.testing.v1 import AppTest
    from test_launch import APP
    from db import StudyRepository

    saved = {}
    def browser(action, value=None):
        if action == 'write':
            saved.clear()
            saved.update(deepcopy(value))
        return deepcopy(saved)
    monkeypatch.setattr('launch.browser_bridge', browser)
    at, calls, deck = setup(monkeypatch)
    client = at.session_state['auth'].client
    client.auth.get_session.return_value = SimpleNamespace(access_token='access', refresh_token='refresh')
    original = StudyRepository.action
    def with_options(repo, action, data=None):
        result = original(repo, action, data)
        if action == 'list':
            result['decks'].append(dict(result['decks'][0], id='second', course='Economics', name='Microeconomics'))
        if action == 'friend_options':
            return {'friends': [{'id':'f1','username':'Alex'}, {'id':'f2','username':'Sam'}]}
        return result
    monkeypatch.setattr(StudyRepository, 'action', with_options)
    def reopen():
        fresh = AppTest.from_file(str(APP), default_timeout=20)
        fresh.session_state['auth'] = AuthService(client)
        fresh.run()
        assert not fresh.exception
        return fresh
    def widget(widgets, label):
        return next(w for w in widgets if w.label == label)

    at.run()
    widget(at.selectbox, 'Study course').set_value('Economics').run()
    widget(at.multiselect, 'Chapters / lectures (leave empty for full deck)').set_value(['Lecture 1']).run()
    at.checkbox(key='study_solo_levels_1').uncheck().run()
    widget(at.number_input, 'Number of questions').set_value(6).run()
    at = reopen()
    assert at.session_state.study_choice == 'Study alone'
    assert widget(at.selectbox, 'Study course').value == 'Economics'
    assert widget(at.selectbox, 'Select quiz deck').value == 'second'
    assert at.multiselect[0].value == ['Lecture 1']
    assert not at.checkbox(key='study_solo_levels_1').value
    assert widget(at.number_input, 'Number of questions').value == 6
    widget(at.radio, 'Session length').set_value('All matching questions').run()
    at = reopen()
    assert widget(at.radio, 'Session length').value == 'All matching questions'
    button(at,'Back to Study alone').click().run()
    button(at,'Change study mode').click().run()
    button(at,'Study together').click().run()
    button(at,'Create a new study session').click().run()
    button(at,'Friend').click().run()
    widget(at.selectbox,'Choose a friend').set_value('f2').run()
    widget(at.selectbox,'Total questions').set_value(40).run()
    at.checkbox(key='study_together_levels_2').uncheck().run()
    next(w for w in at.checkbox if w.label.startswith('I agree')).check().run()
    at = reopen()
    assert at.session_state.study_choice == 'Study together'
    assert widget(at.selectbox,'Choose a friend').value == 'f2'
    assert widget(at.selectbox,'Total questions').value == 40
    assert not at.checkbox(key='study_together_levels_2').value
    assert not next(w for w in at.checkbox if w.label.startswith('I agree')).value
    at.run()
    assert widget(at.selectbox,'Choose a friend').value == 'f2'
    assert widget(at.selectbox,'Total questions').value == 40

    saved['study_setup'].update(course='Gone', deck='deleted', friend='removed', total=-1,
                                join='expired', levels={'invalid':True})
    at = reopen()
    assert widget(at.selectbox,'Choose a friend').value in ('f1','f2')
    assert widget(at.selectbox,'Total questions').value == 20
    assert not at.session_state.get('study_join')
    restored = deepcopy(saved)
    button(at,'Back to Study together').click().run()
    button(at,'Change study mode').click().run()
    assert 'study_setup' not in saved
    button(at,'Study alone').click().run()
    button(at,'Profile').click().run()
    at = reopen()
    assert at.session_state.main_page == 'Profile'
    assert 'study_setup' not in saved
    saved.update(restored, user_id='different-account')
    at = reopen()
    assert not at.session_state.get('study_active')
    assert 'study_setup' not in saved
    assert not any(action in ('start','answer','next','decline') for action,_ in calls)


def test_waiting_friend_session_stays_visible_while_another_invitation_can_open(monkeypatch):
    at, calls, deck = setup(monkeypatch)
    from db import StudyRepository
    original = StudyRepository.action
    sessions = [dict(id='busy', mode='friend', state='waiting', cursor=10, count=20, name='Finance', friend_username='Alex', expires_at='2026-12-01T12:00:00+00:00')]
    def action(self, kind, data=None):
        if kind == 'stop':
            assert data == {'id':'busy'}
            sessions.clear()
            return {}
        result = original(self, kind, data)
        if kind == 'list':
            result.update(sessions=sessions, invites=[dict(id='invite', username='Alex',
                          course='Finance', language='English', count=20)])
        return result
    monkeypatch.setattr(StudyRepository, 'action', action)
    button(at,'Back to Study alone').click().run()
    button(at,'Change study mode').click().run()
    assert at.tabs[-1].label == 'Invitations'
    button(at,'Accept invitation').click().run()
    assert at.session_state['study_join'] == 'invite' and at.session_state['study_creating']
    assert not at.exception
