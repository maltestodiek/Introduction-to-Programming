"""Acceptance contract for review; auth.py has not been implemented."""
from types import SimpleNamespace as Obj
from unittest.mock import Mock
import pytest
from auth import AuthService

def provider():
    p = Mock()
    p.auth.sign_in_with_password.return_value = Obj(session=Obj(access_token="test-token"))
    p.auth.get_user.return_value = Obj(user=Obj(id="student-a", email="a@example.test"))
    p.auth.sign_up.return_value = Obj(user=Obj(id="student-a"), session=None)
    return p

def test_signup_waits_for_confirmation():
    p = provider()
    service = AuthService(p)
    result = service.sign_up("a@example.test", "Test-password-123", "Test-password-123")
    assert result.status == "check_email"
    assert service.user is None

@pytest.mark.parametrize("email,password,confirmation", [
    ("", "Test-password-123", "Test-password-123"),
    ("invalid", "Test-password-123", "Test-password-123"),
    ("a@example.test", "", ""),
    ("a@example.test", "Test-password-123", "Different-password-123"),
])
def test_invalid_signup_never_contacts_provider(email, password, confirmation):
    p = provider()
    service = AuthService(p)
    assert service.sign_up(email, password, confirmation).status == "invalid_input"
    p.auth.sign_up.assert_not_called()
    assert service.user is None

def test_valid_login_requires_verified_identity():
    p = provider()
    service = AuthService(p)
    assert service.sign_in("a@example.test", "Test-password-123").status == "signed_in"
    assert service.user.id == "student-a"
    p.auth.get_user.assert_called()

def test_session_without_verified_user_is_rejected():
    p = provider()
    p.auth.get_user.return_value = Obj(user=None)
    service = AuthService(p)
    assert service.sign_in("a@example.test", "Test-password-123").status != "signed_in"
    assert service.user is None

def test_provider_failure_is_safe_and_locked():
    p = provider()
    p.auth.sign_in_with_password.side_effect = Exception("PRIVATE PROVIDER DETAIL")
    service = AuthService(p)
    result = service.sign_in("a@example.test", "wrong-password")
    assert result.status != "signed_in"
    assert "PRIVATE PROVIDER DETAIL" not in result.message
    assert service.user is None

def test_sessions_are_isolated():
    first = AuthService(provider())
    second = AuthService(provider())
    first.sign_in("a@example.test", "Test-password-123")
    assert first.user is not None
    assert second.user is None

@pytest.mark.parametrize("remote_failure", [False, True])
def test_logout_clears_identity_even_on_remote_failure(remote_failure):
    p = provider()
    service = AuthService(p)
    service.sign_in("a@example.test", "Test-password-123")
    if remote_failure:
        p.auth.sign_out.side_effect = Exception("provider unavailable")
    service.sign_out()
    assert service.user is None

def test_fresh_service_starts_signed_out():
    service = AuthService(provider())
    assert service.user is None
