from db import battle_error_message


def test_battle_error_message_keeps_eligibility_feedback():
    error=Exception("{'message': 'No eligible Battle Deck is available for this course and language'}")
    assert battle_error_message(error).startswith('Not able to start this Battle')


def test_battle_error_message_hides_unknown_database_details():
    assert battle_error_message(Exception('column private_data is ambiguous')).startswith('Battle Mode could not be reached')


def test_battle_error_message_labels_an_existing_invitation():
    error=Exception('There is already a pending Battle invitation between you')
    assert battle_error_message(error).startswith('Outstanding invitation')
