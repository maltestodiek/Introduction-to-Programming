from types import SimpleNamespace

from db import BattleRepository,battle_error_message,question_report_error_message


def test_battle_error_message_keeps_eligibility_feedback():
    error=Exception("{'message': 'No eligible Battle Deck is available for this course and language'}")
    assert battle_error_message(error).startswith('Not able to start this Battle')


def test_battle_error_message_hides_unknown_database_details():
    assert battle_error_message(Exception('column private_data is ambiguous')).startswith('Battle Mode could not be reached')


def test_course_search_conflict_explains_that_the_same_course_is_already_pending():
    message=battle_error_message(Exception('You are already searching for a random player for this course'))
    assert message=='You are already searching for a random player for this course. Manage or cancel the existing search in Active battles.'


def test_cancel_search_targets_only_requested_course():
    calls=[]
    class Client:
        def rpc(self,name,data):
            calls.append((name,data))
            return SimpleNamespace(execute=lambda:SimpleNamespace(data={'cancelled':True}))
    assert BattleRepository(Client()).cancel_search('Finance')['cancelled']
    assert calls==[('cancel_battle_search',{'p_course':'Finance'})]


def test_battle_error_message_labels_an_existing_invitation():
    error=Exception('There is already a pending Battle invitation between you')
    assert battle_error_message(error).startswith('Outstanding invitation')


def test_question_report_uses_the_participant_only_database_function():
    calls=[]
    class Client:
        def rpc(self,name,data):
            calls.append((name,data))
            return SimpleNamespace(execute=lambda:SimpleNamespace(data={'reported':True}))
    assert BattleRepository(Client()).report_question('session-1',4,'unclear_question','Please clarify.')=={'reported':True}
    assert calls==[('report_battle_question',{
        'p_session':'session-1','p_card_index':4,
        'p_reason':'unclear_question','p_note':'Please clarify.',
    })]


def test_question_report_error_identifies_a_missing_database_migration():
    error=Exception('Could not find the function public.report_battle_question in the schema cache')
    assert question_report_error_message(error).startswith('Question reports are not set up yet.')
