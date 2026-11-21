from unittest.mock import Mock
from types import SimpleNamespace
from auth import AuthService

def test_reset_email_validates_before_contacting_supabase():
    client=Mock();service=AuthService(client)
    assert service.request_password_reset('bad').status=='invalid_input'
    client.auth.reset_password_for_email.assert_not_called()
    assert service.request_password_reset('student@example.com').status=='check_email'
    client.auth.reset_password_for_email.assert_called_once_with('student@example.com',{'redirect_to':'http://localhost:8501'})
    assert service.user is None

def test_recovery_failure_does_not_unlock_password_change():
    client=Mock();service=AuthService(client)
    client.auth.set_session.side_effect=RuntimeError('private detail')
    result=service.begin_recovery({'type':'recovery','access_token':'test','refresh_token':'test'})
    assert result.status=='error' and 'private detail' not in result.message
    assert service.update_password('password123','password123').status=='error'
    client.auth.update_user.assert_not_called()

def test_verified_recovery_checks_password_and_updates_via_supabase():
    client=Mock();client.auth.get_user.return_value=SimpleNamespace(user=SimpleNamespace(id='test'))
    service=AuthService(client)
    assert service.begin_recovery({'type':'recovery','access_token':'test','refresh_token':'test'}).status=='recovery_ready'
    assert service.update_password('short','short').status=='invalid_input'
    assert service.update_password('password123','different').status=='invalid_input'
    client.auth.update_user.assert_not_called()
    assert service.update_password('password123','password123').status=='password_updated'
    client.auth.update_user.assert_called_once_with({'password':'password123'})
    assert service.user is None and not service.recovery_verified

def test_invalid_redirect_does_not_set_session():
    client=Mock();service=AuthService(client)
    assert service.begin_recovery({'type':'signup'}).status=='error'
    client.auth.set_session.assert_not_called()


def test_hosted_email_redirects_use_configured_public_url():
    client=Mock(); service=AuthService(client,app_url="https://studyduel-example.streamlit.app/")
    service.request_password_reset("student@example.com")
    assert client.auth.reset_password_for_email.call_args.args[1]["redirect_to"]=="https://studyduel-example.streamlit.app"
    service.sign_up("student@example.com","password123","password123","student_a")
    assert client.auth.sign_up.call_args.args[0]["options"]["email_redirect_to"]=="https://studyduel-example.streamlit.app"


def test_new_tab_exchanges_recovery_code_before_showing_form(monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest

    client = Mock()
    verified = SimpleNamespace(id="demo-student")
    client.auth.get_user.return_value = SimpleNamespace(user=verified)
    client.auth.exchange_code_for_session.return_value = SimpleNamespace(session=object(), user=verified)
    monkeypatch.setattr("recovery.recovery_callback", lambda: {
        "type": "recovery", "code": "test-code", "verifier": "test-verifier"
    })
    page = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=20)
    page.session_state["auth"] = AuthService(client)
    page.query_params["code"] = "test-code"
    page.run()
    assert not page.exception
    assert [field.label for field in page.text_input] == ["New password", "Confirm new password"]
    assert "code" not in page.query_params
    client.auth.exchange_code_for_session.assert_called_once_with({
        "auth_code": "test-code", "code_verifier": "test-verifier"
    })


def test_missing_or_rejected_recovery_proof_keeps_password_locked():
    client = Mock()
    service = AuthService(client)
    assert service.begin_recovery({"type": "recovery", "code": "test-code"}).status == "error"
    client.auth.exchange_code_for_session.assert_not_called()
    client.auth.exchange_code_for_session.side_effect = ValueError("expired")
    data = {"type": "recovery", "code": "test-code", "verifier": "wrong"}
    assert service.begin_recovery(data).status == "error"
    assert service.update_password("password123", "password123").status == "error"
    client.auth.update_user.assert_not_called()


def test_reset_proof_matches_the_challenge_sent_by_the_installed_sdk(monkeypatch):
    import base64
    import hashlib
    from supabase import create_client

    client = create_client("https://example.supabase.co", "sb_publishable_test_only")
    request = Mock()
    monkeypatch.setattr(client.auth, "_request", request)
    service = AuthService(client)
    assert service.request_password_reset("student@example.com").status == "check_email"
    proof = service.recovery_verifier()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(proof.encode()).digest()).decode().rstrip("=")
    assert request.call_args.kwargs["body"]["code_challenge_method"] == "s256"
    assert request.call_args.kwargs["body"]["code_challenge"] == challenge
