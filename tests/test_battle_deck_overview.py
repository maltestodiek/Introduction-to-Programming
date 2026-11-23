from pathlib import Path
from unittest.mock import Mock

from streamlit.testing.v1 import AppTest

from auth import AuthService
from logic import DEFAULT_AVATAR
from test_deck_ui import Obj


BATTLE_OVERVIEW_CSS=(Path(__file__).parents[1]/'assets'/'battle-overview.css').read_text()
APP=(Path(__file__).parents[1]/'app.py').read_text()

def overview(monkeypatch,study_decks=None):
    profile={'username':'student_a','university':'Example University','courses':['Corporate Finance','Investments'],'languages':['English'],'avatar':DEFAULT_AVATAR,'image_mode':'Avatar'}
    monkeypatch.setattr('db.ProfileRepository.load',lambda self:profile)
    monkeypatch.setattr('db.DeckRepository.list',lambda self,course:[{'id':'legacy-1','name':'Old classic duel deck','course':course,'language':'English','creator_id':'a','profiles':{'username':'student_a'}}])
    monkeypatch.setattr('db.StudyRepository.publication',lambda self,action,data=None:{'decks':[
        {'id':'study-1','name':'WACC basics','course':'Corporate Finance','language':'English','author':'student_a','count':20,'owned':True},
    ] if study_decks is None else study_decks} if action=='list' else {})
    client=Mock();client.auth.get_user.return_value=Obj(user=Obj(id='a'))
    auth=AuthService(client);auth.user=client.auth.get_user.return_value.user
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=20)
    at.session_state['auth']=auth;at.session_state['main_page']='Decks';at.run()
    return at


def test_each_course_search_filters_only_its_own_study_decks(monkeypatch):
    at=overview(monkeypatch,[
        {'id':'study-wacc','name':'WACC basics','course':'Corporate Finance','language':'English','author':'student_a','count':20,'owned':True},
        {'id':'study-bond','name':'Bond pricing','course':'Corporate Finance','language':'English','author':'student_b','count':12,'owned':False},
        {'id':'study-investments','name':'Bond portfolio','course':'Investments','language':'English','author':'student_c','count':15,'owned':False},
    ])
    at.text_input(key='course_study_search_0').set_value('bond').run()
    # The matching Finance result is shown directly below its search field;
    # only the untouched Investments course retains its dropdown.
    assert len(at.expander)==1
    names=[item.value for item in at.markdown]
    assert any('Bond pricing' in name for name in names)
    assert not any('WACC basics' in name for name in names)
    assert "if query:" in APP and "course_list_results_" in APP
    assert not at.exception


def test_course_search_shows_an_empty_message_without_changing_study_count(monkeypatch):
    at=overview(monkeypatch)
    at.text_input(key='course_study_search_0').set_value('missing').run()
    assert len(at.expander)==1
    assert any('No Study decks in Corporate Finance match your search.' in item.value for item in at.caption)
    # The filter changes the expanded results, not the course's total deck count.
    assert "str(study_count)+' Deck'" in APP


def test_course_card_shows_only_study_deck_counts(monkeypatch):
    at=overview(monkeypatch)
    labels=[item.label for item in at.expander]
    assert labels.count('View all study decks')==2
    course_section=APP[APP.index("st.subheader('Your courses')"):APP.index('def deck_studio_timezone')]
    assert 'Battle decks' not in course_section


def test_decks_screen_hides_browse_and_battle_deck_actions(monkeypatch):
    at=overview(monkeypatch)
    labels=[item.label for item in at.button]
    assert 'Start Battle' not in labels
    assert 'Battle' not in labels
    assert labels.count('Study')==1
    assert not any(item.value=='Browse decks' for item in at.subheader)
    assert not at.segmented_control
    assert not at.exception


def test_decks_screen_does_not_query_the_battle_catalogue(monkeypatch):
    monkeypatch.setattr('db.BattleRepository.catalog',lambda self:(_ for _ in ()).throw(AssertionError('must not load Battle decks')))
    at=overview(monkeypatch)
    assert not at.warning
    assert not at.exception


def test_battle_dashboard_uses_distinct_ongoing_pending_and_completed_columns():
    assert '.st-key-battle_overview_group_ongoing{background:var(--sd-battle-end)!important}' in BATTLE_OVERVIEW_CSS
    assert '.st-key-battle_overview_group_pending{background:var(--sd-surface-muted)!important}' in BATTLE_OVERVIEW_CSS
    assert '.st-key-battle_overview_group_completed{background:var(--sd-study-end)!important}' in BATTLE_OVERVIEW_CSS
    assert '.st-key-battle_game_overview{margin-top:1rem;border:1px solid var(--sd-border)!important' in BATTLE_OVERVIEW_CSS
    assert '.st-key-battle_dashboard_hero{overflow:hidden' in BATTLE_OVERVIEW_CSS
    assert '.st-key-battle_session_history{margin-top:1rem' in BATTLE_OVERVIEW_CSS


def test_battle_dashboard_shows_the_persisted_win_streak_next_to_the_rank():
    assert 'profile.get("win_streak",0)' in APP
    assert '<span>Win streak</span>' in APP


def test_battle_history_and_overview_cards_use_the_requested_compact_layout():
    assert "st.subheader('Battle history')" in APP
    assert '.st-key-battle_session_history h3{font-size:1.65rem!important' in BATTLE_OVERVIEW_CSS
    assert 'card_completed_"] button,[class*="st-key-battle_overview_invite_"] button{font-size:1rem!important}' in BATTLE_OVERVIEW_CSS
    assert 'button p{font-family:inherit!important;font-size:1rem!important' in BATTLE_OVERVIEW_CSS
    assert 'grid-template-rows:4rem 2rem 2rem' in BATTLE_OVERVIEW_CSS
    assert '-webkit-line-clamp:2' in BATTLE_OVERVIEW_CSS


def test_recent_result_cards_keep_long_deck_names_on_one_line():
    assert '.bo-deck{margin:0 0 .5rem!important;color:var(--sd-muted);font-size:.60rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' in BATTLE_OVERVIEW_CSS


def test_overview_lanes_put_ongoing_beside_pending_and_completed_below():
    section=APP[APP.index('def battle_session_overview'):APP.index('def battle_session_history')]
    assert "st.columns(2,gap='medium')" in section
    assert section.index("st.columns(2,gap='medium')")<section.index("battle_overview_group_completed")
    assert "columns=st.columns(3,gap='medium')" in section
    assert '.st-key-battle_overview_group_completed{margin-top:1.1rem' in BATTLE_OVERVIEW_CSS
    assert ':is(.st-key-battle_overview_group_ongoing,.st-key-battle_overview_group_pending) .bo-empty{min-height:9rem' in BATTLE_OVERVIEW_CSS


def test_overview_cards_present_battles_as_versus_duels():
    section=APP[APP.index('def battle_session_overview'):APP.index('def battle_session_history')]
    assert 'bo-av bo-av-me' in section and 'bo-av bo-av-op' in section
    assert 'Waiting for ' in section and 'bo-wait' in section
    assert '{trophy}{result}' in section and '{xp:+d} XP' in section
    assert '[class*="st-key-battle_overview_card_completed_"]:has(.bo-win){border-left:5px solid var(--sd-success-border)!important}' in BATTLE_OVERVIEW_CSS
    assert '[class*="st-key-battle_overview_card_completed_"]:has(.bo-loss){border-left:5px solid var(--sd-danger-border)!important}' in BATTLE_OVERVIEW_CSS
    assert '[class*="st-key-battle_overview_card_ongoing_"]{border:2px solid var(--sd-accent)!important;animation:bo-live' in BATTLE_OVERVIEW_CSS
    assert '.bo-empty' in BATTLE_OVERVIEW_CSS


def test_pending_invitation_card_lists_the_deck_before_status_opponent_and_course():
    assert 'battle-overview-card-copy' in APP
    assert "escape(str(invite['course']))" in APP
    assert 'strong title="'+"'+safe_deck+'" in APP


def test_invitation_cards_show_the_senders_avatar_beside_the_name():
    assert "opponent_face(invite.get('image_path'))" in APP
    assert 'bo-person' in APP
    assert '.bo-person{display:flex;align-items:center;gap:8px}' in BATTLE_OVERVIEW_CSS


def test_versus_cards_show_real_avatar_faces_for_both_players():
    section=APP[APP.index('def battle_session_overview'):APP.index('def battle_session_history')]
    assert 'self_avatar_url(image_repo,profile)' in section
    assert "versus_markup(opponent,session.get('opponent_image_path'))" in section
    assert section.count("session.get('opponent_image_path')")==2
    assert '.bo-av img{width:100%;height:100%;object-fit:cover;border-radius:50%;display:block}' in BATTLE_OVERVIEW_CSS
    from pathlib import Path
    migration=(Path(__file__).parents[1]/'supabase'/'migrations'/'20261123120000_battle_avatars.sql').read_text()
    assert "'opponent_image_path',p.image_path" in migration
    assert "raise exception 'Cannot install Battle invite avatars" in migration


def test_the_own_avatar_prefers_the_photo_and_falls_back_to_the_configured_face():
    section=APP[APP.index('def self_avatar_url'):APP.index('def chat_list_item')]
    assert "chat_person_avatar(image_repo,{'image_path':path})" in section
    assert "render_avatar((profile or {}).get('avatar') or DEFAULT_AVATAR)" in section


def test_incoming_battle_invitation_is_marked_as_new_and_has_a_primary_accept_action():
    assert "battle_overview_invite_received_" in APP
    assert "show_play_update('battle','invite',invite['id'])" in APP
    assert "accept.button('Accept',key='battle_accept_'+invite['id'],type='primary'" in APP


def test_the_battle_screen_has_no_back_button_the_sidebar_play_entry_covers_it():
    assert 'Back to Play mode selection' not in APP
