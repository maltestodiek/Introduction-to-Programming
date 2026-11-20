from pathlib import Path

from round_effects import countdown_overlay, streak_length, streak_milestone

ROOT=Path(__file__).parents[1]
APP=(ROOT/'app.py').read_text()
EFFECTS_CSS=(ROOT/'assets'/'round-effects.css').read_text()
BATTLE_CSS=(ROOT/'assets'/'battle-round.css').read_text()
STUDY_CSS=(ROOT/'assets'/'study-round.css').read_text()


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


def test_countdown_overlay_counts_down_and_ends_on_the_mode_emblem():
    battle=countdown_overlay('battle')
    study=countdown_overlay('study',decorative=True)
    for digit in ('>3<','>2<','>1<','round-mode-icon'):
        assert digit in battle and digit in study
    assert 'GO!' not in battle
    assert 'battle-emblem' in battle and 'study-emblem' in study
    assert 'Battle starting' in battle and 'Study starting' in study
    assert 'is-decorative' in study and 'is-decorative' not in battle


def test_countdown_overlay_blocks_no_clicks_and_respects_reduced_motion():
    assert 'pointer-events:none' in EFFECTS_CSS
    assert '.round-countdown' in EFFECTS_CSS
    assert '.round-mode-icon .sword-left{transform:rotate(-38deg)' in EFFECTS_CSS
    assert '.round-mode-icon .sword-right{transform:rotate(38deg)' in EFFECTS_CSS
    # The emblem must still be on screen when the first question replaces the overlay.
    assert '@keyframes round-go{0%{opacity:0;transform:scale(.4)}40%{opacity:1;transform:scale(1.25)}70%{transform:scale(1)}100%{opacity:1;transform:scale(1)}}' in EFFECTS_CSS
    assert 'time.sleep(4.5)' in APP
    assert '@media(prefers-reduced-motion:reduce)' in EFFECTS_CSS


def test_battle_requests_the_first_question_only_after_the_countdown():
    assert "st.session_state.get(countdown_key)" in APP
    section=APP[APP.index('def battle_round_screen'):APP.index('def battle_game_dialog')]
    assert "countdown_overlay('battle')" in section
    assert section.index('battle_countdown_')<section.index("battle_request(client,'round'")


def test_study_round_shows_a_decorative_countdown_once():
    assert 'study_countdown_' in APP
    assert "countdown_overlay('study',decorative=True)" in APP


def test_streak_badge_sits_beside_the_overview_heading_in_both_modes():
    assert '.round-overview-head{display:flex;align-items:center;justify-content:space-between' in EFFECTS_CSS
    assert APP.count('<div class="round-overview-head"><h3>Overview</h3>')==2
    assert "round-streak" not in APP[APP.index("st.caption(f\"Question"):APP.index("st.caption(f\"Question")+600]


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
    assert "battle_request(client,'abandon',{'id':session_id,'confirmed':True})" in section
    assert 'Keep fighting' in section and 'Leave Battle' in section
    assert '[class*="st-key-round_leave_modal_"]{position:fixed;z-index:2200;top:50%;left:50%;transform:translate(-50%,-50%)' in EFFECTS_CSS
    assert '.round-modal-backdrop{position:fixed;inset:0' in EFFECTS_CSS
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
