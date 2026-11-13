import io
import json
from unittest.mock import patch
from urllib.error import URLError
import pytest
from universities import search_universities, UniversitySearchError

def test_ror_search_filters_and_formats_education_results():
    payload={"items":[{"id":"https://ror.org/123abc","status":"active","types":["education"],
       "names":[{"value":"Example University","types":["ror_display"]}],
       "locations":[{"geonames_details":{"country_name":"Portugal"}}]},
       {"types":["company"],"names":[{"value":"Other","types":["ror_display"]}]}]}
    with patch("universities.urlopen",return_value=io.BytesIO(json.dumps(payload).encode())) as call:
        result=search_universities("Example")
    assert result==[{"name":"Example University","country":"Portugal","label":"Example University — Portugal","id":"https://ror.org/123abc"}]
    assert "filter=types%3Aeducation" in call.call_args.args[0].full_url
    assert call.call_args.kwargs["timeout"]==8

def test_ror_empty_result_is_not_an_error():
    with patch("universities.urlopen",return_value=io.BytesIO(b'{"items":[]}')):
        assert search_universities("Missing")==[]

def test_ror_outage_keeps_manual_fallback():
    with patch("universities.urlopen",side_effect=URLError("offline")):
        with pytest.raises(UniversitySearchError,match="type your university"):
            search_universities("Example")

@pytest.mark.parametrize("query",["","x","x"*121])
def test_query_validation(query):
    with pytest.raises(ValueError):search_universities(query)

def test_custom_avatar_choice_is_preserved_and_unknown_values_rejected():
    from avatar_picker import clean_selection
    from logic import DEFAULT_AVATAR
    saved=clean_selection(dict(DEFAULT_AVATAR,hair="Mohawk",accessory="Crown"),DEFAULT_AVATAR)
    assert saved["hair"]=="Mohawk" and saved["accessory"]=="Crown"
    assert clean_selection({"hair":"invalid"},DEFAULT_AVATAR)==DEFAULT_AVATAR
