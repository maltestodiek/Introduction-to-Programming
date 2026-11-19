from types import SimpleNamespace as Obj
from unittest.mock import Mock
import pytest

from db import AnkiImportRepository


def test_generation_sends_only_import_and_selected_source_ids():
    client=Mock()
    client.functions.invoke.return_value=Obj(data={'count':2,'status':'draft'})
    result=AnkiImportRepository(client).generate('import-1',['card-1','card-2'])
    assert result=={'count':2,'status':'draft'}
    client.functions.invoke.assert_called_once_with('generate-questions',invoke_options={'body':{'importId':'import-1','cardIds':['card-1','card-2']}})


@pytest.mark.parametrize('cards',[[],['card']*101])
def test_generation_rejects_invalid_selection_before_network_call(cards):
    client=Mock()
    with pytest.raises(ValueError,match='between 1 and 100'):
        AnkiImportRepository(client).generate('import-1',cards)
    client.functions.invoke.assert_not_called()


def test_unexpected_generation_response_does_not_claim_success():
    client=Mock()
    client.functions.invoke.return_value=Obj(data={'count':1})
    with pytest.raises(ValueError,match='unexpected result'):
        AnkiImportRepository(client).generate('import-1',['card-1'])


def test_generation_keeps_the_safe_error_returned_by_the_edge_function():
    class FunctionError(Exception): pass
    response=Mock()
    response.json.return_value={'error':'The AI provider could not generate questions (HTTP 402).'}
    client=Mock()
    error=FunctionError()
    error.context=response
    client.functions.invoke.side_effect=error
    with pytest.raises(ValueError,match='HTTP 402'):
        AnkiImportRepository(client).generate('import-1',['card-1'])


def test_generation_falls_back_to_the_function_client_error_when_no_response_is_available():
    client=Mock()
    client.functions.invoke.side_effect=Exception('Server returned HTTP 502')
    with pytest.raises(ValueError,match='HTTP 502'):
        AnkiImportRepository(client).generate('import-1',['card-1'])


@pytest.mark.parametrize('raw',[b'{"count":18,"status":"draft"}','{"count":18,"status":"draft"}',bytearray(b'{"count":18,"status":"draft"}')])
def test_generation_accepts_the_raw_json_body_returned_by_supabase_functions(raw):
    # supabase-py returns response.content (bytes) unless responseType is "json".
    client=Mock()
    client.functions.invoke.return_value=raw
    assert AnkiImportRepository(client).generate('import-1',['card-1'])=={'count':18,'status':'draft'}


@pytest.mark.parametrize('raw',[b'not json',b'[]',b'{"count":1}'])
def test_unreadable_raw_generation_body_does_not_claim_success(raw):
    client=Mock()
    client.functions.invoke.return_value=raw
    with pytest.raises(ValueError,match='unexpected result'):
        AnkiImportRepository(client).generate('import-1',['card-1'])
