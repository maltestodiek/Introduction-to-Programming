from unittest.mock import Mock
import pytest
from db import DeckRepository
from test_deck_rules import complete_deck

def test_review_and_publish_only_exact_snapshot():
    client=Mock();client.rpc.return_value.execute.return_value.data={'id':'review-id'}
    repo=DeckRepository(client);draft=complete_deck();review=repo.review(draft)
    assert client.rpc.call_args.args[0]=='review_deck'
    assert 'creator_id' not in client.rpc.call_args.args[1]
    draft['name']='Changed'
    with pytest.raises(ValueError,match='review'):repo.publish(draft,review)
    assert client.rpc.call_count==1

def test_invalid_draft_never_writes():
    client=Mock();d=complete_deck();d['cards'].pop()
    with pytest.raises(ValueError):DeckRepository(client).review(d)
    client.rpc.assert_not_called()
