from unittest.mock import Mock
import pytest
from logic import validate_profile
from db import ProfileRepository
from test_storage import payload

@pytest.mark.parametrize("year", [None, 2000, 2028, 2100])
def test_optional_graduation_year_is_saved(year):
    data = dict(payload(), graduation_year=year)
    assert validate_profile(**data)["graduation_year"] == year
    client = Mock()
    ProfileRepository(client, "owner").save(data, "Avatar", None, None)
    assert client.rpc.call_args.args[0] == "save_profile_v3"
    assert client.rpc.call_args.args[1]["p_graduation_year"] == year

@pytest.mark.parametrize("year", [1999, 2101, True, "2028", 2028.5])
def test_invalid_graduation_does_not_write(year):
    client = Mock()
    with pytest.raises(ValueError, match="graduation"):
        ProfileRepository(client, "owner").save(dict(payload(), graduation_year=year), "Avatar", None, None)
    client.rpc.assert_not_called()
