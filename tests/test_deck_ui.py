from pathlib import Path
from unittest.mock import Mock
from types import SimpleNamespace as Obj
from streamlit.testing.v1 import AppTest
from auth import AuthService
from logic import DEFAULT_AVATAR
from test_deck_rules import complete_deck


def deck_app(monkeypatch):
    profile={'username':'student_a','university':'Example University','courses':['Finance'],'languages':['English'],'avatar':DEFAULT_AVATAR,'image_mode':'Avatar'}
    monkeypatch.setattr('db.ProfileRepository.load',lambda self:profile)
    monkeypatch.setattr('db.DeckRepository.list',lambda self,course:[])
    client=Mock();client.auth.get_user.return_value=Obj(user=Obj(id='a'))
    auth=AuthService(client);auth.user=client.auth.get_user.return_value.user
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=20)
    at.session_state['auth']=auth;at.session_state['main_page']='Decks';at.run()
    return at

def button(at,label):return next(b for b in at.button if b.label==label)

def test_placeholders_disabled_and_incomplete_card_rejected(monkeypatch):
    at=deck_app(monkeypatch)
    assert not button(at,'Import Anki deck').disabled
    assert not button(at,'Generate with AI').disabled
    assert not any(exp.label=='Battle Mode Decks' for exp in at.expander)
    assert 'Create Battle Mode Deck' in [widget.label for widget in at.button]
    assert not any('30-question' in getattr(widget,'value','') for widget in at.markdown)
    assert not at.exception

def test_active_decks_screen_does_not_offer_legacy_thirty_question_authoring(monkeypatch):
    at=deck_app(monkeypatch)
    labels=[widget.label for widget in at.button]
    assert 'Create 15-question duel deck' not in labels
    assert 'Create Battle Mode Deck' in labels
    assert not at.exception


def test_decks_show_a_vertical_course_list_and_filtered_deck_section(monkeypatch):
    profile={'username':'student_a','university':'Example University','courses':['Corporate Finance','Statistics'],'languages':['English'],'avatar':DEFAULT_AVATAR,'image_mode':'Avatar'}
    battle_decks={
        'Corporate Finance':[{'id':'battle-cf','name':'Capital structure','course':'Corporate Finance','language':'English','creator_id':'a','profiles':{'username':'student_a'}}],
        'Statistics':[],
    }
    monkeypatch.setattr('db.ProfileRepository.load',lambda self:profile)
    monkeypatch.setattr('db.DeckRepository.list',lambda self,course:battle_decks[course])
    monkeypatch.setattr('db.StudyRepository.publication',lambda self,action,data=None:{'decks':[
        {'id':'study-stats','name':'Regression recap','course':'Statistics','language':'English','author':'Student B','count':12,'owned':False},
    ]} if action=='list' else {})
    client=Mock();client.auth.get_user.return_value=Obj(user=Obj(id='a'))
    auth=AuthService(client);auth.user=client.auth.get_user.return_value.user
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=20)
    at.session_state['auth']=auth;at.session_state['main_page']='Decks';at.run()
    headings=[item.value for item in at.subheader]
    assert headings.count('Your courses')==1 and 'Browse decks' not in headings
    assert next(field for field in at.text_input if field.label=='Search Corporate Finance Study decks')
    assert next(field for field in at.text_input if field.label=='Search Statistics Study decks')
    expander_labels=[item.label for item in at.expander]
    assert expander_labels.count('View all study decks')==2
    assert not any(field.label=='Browse course' for field in at.selectbox)
    assert len([item for item in at.button if item.label=='Study'])==1
    assert not any(item.label in ('Battle','Start Battle') for item in at.button)
    assert not any(item.label=='Daily review' for item in at.button)
    assert not at.exception


def test_battle_deck_creator_shows_questions_only_after_choosing_a_source(monkeypatch):
    cards=[{'id':str(index),'question':f'Question {index}'} for index in range(16)]
    def action(self,kind,data=None):
        if kind=='sources':
            return {'sources':[{'id':'source-1','name':'Source','course':'Finance','language':'English','count':16,'battle_capable':True}]}
        if kind=='source':return {'name':'Source','cards':cards}
        raise AssertionError(kind)
    monkeypatch.setattr('db.BattleRepository.action',action)
    at=deck_app(monkeypatch)
    at.session_state['battle_deck_creator']=True;at.run()
    assert next(field for field in at.selectbox if field.label=='Source Study deck').value is None
    assert not at.checkbox
    next(field for field in at.selectbox if field.label=='Source Study deck').set_value('source-1').run()
    assert len(at.checkbox)==17  # 16 questions plus the public-play confirmation.
    assert not any(button.label=='Back to Decks' for button in at.button)


def test_battle_deck_creator_opens_a_dialog_when_selection_is_not_fifteen(monkeypatch):
    cards=[{'id':str(index),'question':f'Question {index}'} for index in range(16)]
    def action(self,kind,data=None):
        if kind=='sources':
            return {'sources':[{'id':'source-1','name':'Source','course':'Finance','language':'English','count':16,'battle_capable':True}]}
        if kind=='source':return {'name':'Source','cards':cards}
        raise AssertionError(kind)
    monkeypatch.setattr('db.BattleRepository.action',action)
    at=deck_app(monkeypatch)
    at.session_state['battle_deck_creator']=True;at.run()
    next(field for field in at.selectbox if field.label=='Source Study deck').set_value('source-1').run()
    for checkbox in at.checkbox[:16]:checkbox.check().run()
    button(at,'Submit Battle Deck').click().run()
    assert any('exactly 15 questions' in error.value for error in at.error)
    assert any(button.label=='Continue selecting' for button in at.button)
    assert not at.exception


def test_new_battle_opens_a_dedicated_setup_screen(monkeypatch):
    def action(self,kind,data=None):
        if kind=='list':return {'sessions':[],'invites':[],'search':None}
        if kind=='friend_options':return {'friends':[]}
        return {}
    monkeypatch.setattr('db.BattleRepository.action',action)
    at=deck_app(monkeypatch)
    button(at,'Play').click().run()
    button(at,'Battle Mode').click().run()
    assert any(item.value=='Game Overview' for item in at.subheader)
    button(at,'New Battle').click().run()
    assert any(item.value=='Start a new Battle' for item in at.subheader)
    assert not any(item.value=='Game Overview' for item in at.subheader)
    assert button(at,'Back to Game Overview')
    assert not at.exception


def test_random_battle_search_is_disabled_when_no_eligible_deck_exists(monkeypatch):
    def action(self,kind,data=None):
        if kind=='list':return {'sessions':[],'invites':[],'search':None}
        if kind=='friend_options':return {'friends':[]}
        return {}
    monkeypatch.setattr('db.BattleRepository.action',action)
    monkeypatch.setattr('db.BattleRepository.availability',lambda self,course,language:{'available':False})
    at=deck_app(monkeypatch)
    button(at,'Play').click().run();button(at,'Battle Mode').click().run();button(at,'New Battle').click().run()
    assert button(at,'Start random Battle').disabled
    assert any('No available Battle Decks yet' in warning.value for warning in at.warning)
    assert not at.exception


def test_random_battle_starts_before_matching_and_confirmed_exit_records_loss(monkeypatch):
    state={'sessions':[],'invites':[],'search':None}
    deadline='2099-01-01T16:30:00+00:00'
    def action(self,kind,data=None):
        if kind=='list':return state
        if kind=='start_random':
            assert data['request_id']
            state['sessions']=[dict(id='first',status='ongoing',started=True,waiting_for_match=True,deck_name='Finance',finish_by=deadline)]
            return {'session_id':'first'}
        if kind=='leave':
            assert data=={'id':'first','confirmed':True}
            state['sessions'][0].update(status='completed',waiting_for_match=False,result='loss',score=0,game_xp_delta=0,opponent_username=None,course='Finance')
            return {'state':'completed','result':'loss'}
        if kind=='round':return dict(state='question',index=0,seconds=28,question='First question?',options=[dict(id='a',text='Answer A')])
        raise AssertionError(kind)
    monkeypatch.setattr('db.BattleRepository.action',action)
    monkeypatch.setattr('db.BattleRepository.progress',lambda self,session_id:{'answers':[]})
    monkeypatch.setattr('db.BattleRepository.availability',lambda self,course,language:{'available':True})
    at=deck_app(monkeypatch)
    button(at,'Play').click().run();button(at,'Battle Mode').click().run();button(at,'New Battle').click().run()
    button(at,'Start random Battle').click().run()
    assert button(at,'Answer A')
    button(at,'Leave Battle').click().run()
    assert any('immediate loss' in str(item.value) for item in at.get('html'))
    button(at,'Keep fighting').click().run()
    assert button(at,'Answer A')
    button(at,'Leave Battle').click().run()
    button(at,'Leave and lose').click().run()
    assert not any(b.label=='Resume Battle' for b in at.button)
    assert any('Loss' in str(item.value) and 'No opponent matched' in str(item.value) for item in at.get('html'))
    assert not at.exception


def test_pending_random_battle_search_can_be_cancelled(monkeypatch):
    state={'sessions':[],'invites':[],'search':{'course':'Finance','language':'English','expires_at':'2099-01-01T00:00:00Z'}}
    def action(self,kind,data=None):
        if kind=='list':return state
        return {}
    def cancel_search(self):
        state['search']=None
        return {'cancelled':True}
    monkeypatch.setattr('db.BattleRepository.action',action)
    monkeypatch.setattr('db.BattleRepository.cancel_search',cancel_search)
    at=deck_app(monkeypatch)
    button(at,'Play').click().run();button(at,'Battle Mode').click().run();button(at,'Cancel search').click().run()
    assert any('Battle search cancelled.' in message.value for message in at.success)
    assert any('No battle invitations.' in str(item.value) for item in at.get('html'))
    assert not at.exception


def test_completed_battle_review_offers_a_report_for_each_question(monkeypatch):
    card={
        'id':'card-1','question':'Is this question clear?',
        'answers':[{'id':'answer-1','text':'Yes'},{'id':'answer-2','text':'No'}],
        'correct_answer_id':'answer-1',
    }
    def action(self,kind,data=None):
        if kind=='list':
            return {'sessions':[{
                'id':'session-1','deck_name':'Battle deck','status':'completed',
                'score':1,'opponent_score':1,'result':'draw','game_xp_delta':0,
                'opponent_username':'Opponent','course':'Finance','language':'English',
            }],'invites':[],'search':None}
        if kind=='review':return {'score':1,'cards':[card],'answers':[{'index':0,'answer_id':'answer-1','correct':True}]}
        return {}
    monkeypatch.setattr('db.BattleRepository.action',action)
    at=deck_app(monkeypatch)
    button(at,'Play').click().run()
    button(at,'Battle Mode').click().run()
    button(at,'Review questions').click().run()
    assert any(item.proto.popover.label=='Report this question' for item in at.get('popover'))
    assert not at.exception


def test_decks_page_does_not_include_daily_review_controls():
    from pathlib import Path
    app=(Path(__file__).parents[1]/'app.py').read_text()
    assert 'Daily review' not in app
