from unittest.mock import Mock
import pytest
from db import ProfileRepository
from logic import DEFAULT_AVATAR

def payload():
    return dict(username="student_1",university="Nova SBE — prototype catalog",
        courses=["Corporate Finance"],languages=["English"],avatar=DEFAULT_AVATAR.copy())

def test_failed_save_does_not_remove_previous_image():
    client=Mock()
    client.rpc.return_value.execute.side_effect=Exception("failed")
    repo=ProfileRepository(client,"id-a")
    with pytest.raises(ValueError):
        repo.save(payload(),"Avatar",b"png","id-a/old.png")
    removals=client.storage.from_.return_value.remove.call_args_list
    assert all("id-a/old.png" not in str(c) for c in removals)

def test_saved_payload_does_not_accept_xp_or_another_owner():
    client=Mock()
    repo=ProfileRepository(client,"id-a")
    repo.save(payload(),"Avatar",b"png",None)
    args=client.rpc.call_args.args[1]
    assert "xp" not in args and "user_id" not in args and "win_streak" not in args
    assert args["p_image_path"].startswith("id-a/")
