from unittest.mock import Mock
import pytest
from db import PlayRepository
from logic import new_deck,validate_deck
from test_deck_rules import complete_deck

def test_deck_language_is_required():
    d=complete_deck();d['language']=''
    with pytest.raises(ValueError,match='language'):validate_deck(d)

def test_deck_language_preserved():
    d=complete_deck();d['language']='Portuguese'
    assert validate_deck(d)['language']=='Portuguese'

def test_rpc_uses_server_identity():
    client=Mock();client.rpc.return_value.execute.return_value.data={'queue':None}
    assert PlayRepository(client).action('list')=={'queue':None}
    assert client.rpc.call_args.args==('play_action',{'p_action':'list','p_data':{}})

def test_provider_failure_is_safe():
    client=Mock();client.rpc.return_value.execute.side_effect=Exception('private token')
    with pytest.raises(ValueError,match='Could not confirm') as e:PlayRepository(client).action('join',{'deck_id':'x'})
    assert 'private token' not in str(e.value)
