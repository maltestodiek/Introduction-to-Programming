from pathlib import Path

from round_effects import answered_accuracy, accuracy_chip, combo_markup, countdown_overlay, streak_badge, streak_length, streak_milestone

ROOT=Path(__file__).parents[1]
APP=(ROOT/'app.py').read_text()
EFFECTS_CSS=(ROOT/'assets'/'round-effects.css').read_text()
BATTLE_CSS=(ROOT/'assets'/'battle-round.css').read_text()
STUDY_CSS=(ROOT/'assets'/'study-round.css').read_text()
MODAL_CSS=(ROOT/'assets'/'confirm-modal.css').read_text()


def test_streak_counts_consecutive_correct_answers_up_to_the_latest():
    assert streak_length([])==0
    assert streak_length([{'index':0,'correct':True},{'index':1,'correct':True}])==2
    assert streak_length([{'index':0,'correct':True},{'index':1,'correct':False},{'index':2,'correct':True}])==1
    assert streak_length([{'index':0,'correct':True},{'index':1,'correct':False}])==0


def test_streak_handles_unordered_and_malformed_entries():
    assert streak_length([{'index':2,'correct':True},{'index':0,'correct':True},{'index':1,'correct':True}])==3
    assert streak_length([{'correct':True},'junk',{'index':0,'correct':True}])==1


def test_streak_milestones_are_announced_at_three_five_and_ten():
    assert streak_milestone(2) is None
    assert streak_milestone(3)=='On fire!'
    assert streak_milestone(5)=='Unstoppable!'
    assert streak_milestone(10)=='Legendary!'
    assert streak_milestone(4) is None


def test_intro_shows_the_approved_beats_in_order_for_both_modes():
    for mode in ('battle', 'study'):
        markup=countdown_overlay(mode)
        positions=[markup.index('>'+word+'<') for word in ('3','2','1','Best of Luck!','Go!')]
        assert positions==sorted(positions)
        assert mode.title()+' Mode' in markup
        assert 'aria-label=' in markup


def test_countdown_keeps_the_sidebar_clear_and_supports_reduced_motion():
    css=(ROOT/'assets'/'session-intro.css').read_text()
    assert 'inset:3.75rem 0 0 14rem' in css and '@media(max-width:760px)' in css
    assert 'pointer-events:none' in css and '@media(prefers-reduced-motion:reduce)' in css


def test_battle_start_precedes_first_question_and_resume_skips_intro(monkeypatch):
    from test_deck_ui import deck_app
    events=[]
    monkeypatch.setattr('round_effects.INTRO_SECONDS',0)
    def action(self,action,data=None):
        if action=='list':
            return {'sessions':[{'id':sid,'deck_name':'Finance','status':'ongoing','started':started,
                                 'opponent_username':'Peer'} for sid,started in [('new',False),('opened',True)]]}
        if action=='round':
            events.append(data['id'])
            return {'state':'question','index':0,'seconds':30,'options':[],'question':'First question'}
        return {}
    monkeypatch.setattr('db.BattleRepository.action',action)
    monkeypatch.setattr('db.BattleRepository.progress',lambda *args:{'answers':[]})
    monkeypatch.setattr('round_effects.countdown_overlay',lambda mode: events.append(mode+' intro') or '<p>Intro</p>')
    at=deck_app(monkeypatch)
    at.session_state['main_page']='Play'
    at.session_state['play_mode_preview']='Battle'
    at.run()
    at.button(key='overview_battle_new').click().run()
    assert events==['battle intro','new'] and not at.exception
    del at.session_state['battle_session']
    at.run()
    at.button(key='overview_battle_opened').click().run()
    assert events==['battle intro','new','opened'] and not at.exception


def test_study_start_then_reopen_unanswered_session_skips_intro(monkeypatch):
    from test_deck_ui import button
    from test_study_ui import setup
    from db import StudyRepository
    at,calls,_=setup(monkeypatch)
    original_action=StudyRepository.action
    def action(repo, name, data=None):
        result=original_action(repo,name,data)
        if name=='list' and any(a=='start' for a,_ in calls):
            result['sessions']=[{'id':'session','name':'Practice','mode':'solo','state':'own','cursor':0,'count':10}]
        return result
    monkeypatch.setattr(StudyRepository,'action',action)
    monkeypatch.setattr('round_effects.INTRO_SECONDS',0)
    def intro(mode):
        calls.append(('intro',mode))
        return '<p>Intro</p>'
    monkeypatch.setattr('round_effects.countdown_overlay',intro)
    button(at,'Start studying').click().run()
    assert [a for a,_ in calls if a in ('start','intro','round')]==['start','intro','round']
    button(at,'Save and leave Study session').click().run()
    assert [a for a,_ in calls if a=='intro']==['intro']
    calls_before_resume=len(calls)
    at.button(key='study_resume_session').click().run()
    assert [a for a,_ in calls[calls_before_resume:] if a in ('intro','round')]==['round']
    assert not at.exception


def test_overview_heads_carry_the_live_accuracy_chip_in_both_modes():
    assert '.round-overview-head{display:flex;align-items:center;justify-content:space-between' in EFFECTS_CSS
    assert APP.count('<div class="round-overview-head"><h3>Overview</h3>'+"'+accuracy_chip(")==2
    assert "round-streak" not in APP[APP.index("st.caption(f\"Question"):APP.index("st.caption(f\"Question")+600]


def test_accuracy_is_computed_from_answered_questions_only():
    assert answered_accuracy([]) is None
    assert accuracy_chip([])==''
    answers=[{'index':0,'correct':True},{'index':1,'correct':False},{'index':2,'correct':True}]
    assert answered_accuracy(answers)==67
    assert '67<small>% correct</small>' in accuracy_chip(answers)


def test_streak_badge_and_combo_meter_sit_below_the_tile_grid():
    assert streak_badge(1)=='' and '2 in a row' in streak_badge(2)
    assert 'class="sd-icon"' in streak_badge(2)
    assert APP.count('round-overview-foot')==2
    assert combo_markup(0).count('round-combo-seg"')==5 and 'round-combo-seg on' not in combo_markup(0)
    assert combo_markup(3).count('round-combo-seg on')==3
    assert 'round-combo-full' in combo_markup(7) and combo_markup(7).count('round-combo-seg on')==5
    assert 'round-combo-full' not in combo_markup(7,pulse=False)
    assert "combo_markup(streak,pulse=False)" in APP


def test_battle_review_opens_questions_from_clickable_tiles():
    section=APP[APP.index("@st.dialog('Battle review'"):APP.index('def battle_question_report_form')]
    assert 'st.expander' not in section
    assert "review_tile_{state}_{session_id}_{index}" in section
    assert "st.rerun(scope='fragment')" in section
    assert 'round-review-q' in section and 'Report this question' in section
    assert '[class*="st-key-review_tile_correct"] button{background:var(--sd-success-surface)' in EFFECTS_CSS
    assert '[class*="st-key-review_tile_incorrect"] button{background:var(--sd-danger-surface)' in EFFECTS_CSS
    assert '.round-acc' in EFFECTS_CSS


def test_feedback_effects_exist_for_both_modes():
    assert '.round-confetti' in EFFECTS_CSS
    assert '.round-xp' in EFFECTS_CSS
    assert '.round-vignette' in EFFECTS_CSS
    assert 'is-correct-reveal' in EFFECTS_CSS
    assert '.round-streak' in EFFECTS_CSS
    assert '.round-streak-banner' in EFFECTS_CSS
    assert 'round-tile-flash' in EFFECTS_CSS


def test_only_battle_shows_an_xp_chip():
    assert APP.count('round-xp')==1
    battle_feedback=APP[APP.index('def battle_round_screen'):APP.index('def battle_game_dialog')]
    assert 'round-xp' in battle_feedback


def test_answer_fields_match_the_question_card_height_in_both_modes():
    for css,key in ((BATTLE_CSS,'battle'),(STUDY_CSS,'study')):
        flat=css.replace('\n','')
        assert f'.{key}-answer-card'+'{display:grid;place-items:center;box-sizing:border-box;min-height:110px' in flat
        assert f'.{key}-question-card'+'{border:1px solid var(--sd-border);border-radius:18px;padding:16px 20px;min-height:110px' in flat
        assert f'st-key-{key}_answer_' in EFFECTS_CSS
    assert 'button{min-height:110px' in EFFECTS_CSS
    assert 'button{min-height:96px' in EFFECTS_CSS


def test_the_round_fits_on_screen_without_scrolling_to_timer_or_continue():
    # Compact spacing keeps the timer and the Continue button visible below two 110px answer rows.
    assert 'margin:12px 0 8px' in BATTLE_CSS and 'margin:12px 0 8px' in STUDY_CSS
    assert '.battle-timer-track{height:14px;border-radius:999px;background:var(--sd-border);overflow:hidden;margin-top:14px}' in BATTLE_CSS


def test_leaving_a_battle_asks_in_a_centred_modal_not_a_dropdown():
    section=APP[APP.index('def battle_leave_control'):APP.index('@st.dialog(\'Battle review\'')]
    assert 'st.popover' not in section
    assert "st.container(key=f'round_leave_modal_{session_id}')" in section
    assert 'round-modal-backdrop' in section
    assert "battle_request(client,'clock'" in section and "'abandon'" not in section
    assert 'Keep fighting' in section and 'Save and exit Battle' in section
    assert '[class*="st-key-round_leave_modal_"]{position:fixed;z-index:2200;top:50%;left:50%;transform:translate(-50%,-50%)' in MODAL_CSS
    assert '.round-modal-backdrop{position:fixed;inset:0' in MODAL_CSS
    assert "(Path(__file__).parent/'assets'/'confirm-modal.css').read_text()" in APP
    assert '[class*="st-key-battle_exit_"] button{background:linear-gradient(135deg,#f43f5e,#dc2626)' in BATTLE_CSS


def test_battle_timer_turns_orange_then_red_near_the_end():
    assert '.battle-timer-fill.warning' in BATTLE_CSS
    assert '.battle-timer-fill.urgent' in BATTLE_CSS
    assert "' urgent' if seconds<=5 else ' warning' if seconds<=15 else ''" in APP


def test_question_cards_slide_in():
    assert 'round-slide-in' in EFFECTS_CSS
    assert 'animation:round-slide-in' in BATTLE_CSS and 'animation:round-slide-in' in STUDY_CSS


def test_battle_rating_screen_pops_the_score_with_confetti_for_a_strong_round():
    assert 'round-score' in APP
    assert "score']>=8" in APP.replace('"',"'")
    assert '.round-score' in EFFECTS_CSS
