from types import SimpleNamespace as Obj
from unittest.mock import Mock
from streamlit.testing.v1 import AppTest
from pathlib import Path
from auth import AuthService

APP=Path(__file__).parents[1]/'app.py'

def test_first_visit_start_then_signin():
    at=AppTest.from_file(str(APP)).run()
    assert not at.exception
    assert any(b.label=='Start' for b in at.button)
    assert not at.text_input
    next(b for b in at.button if b.label=='Start').click().run()
    assert any(w.label=='Email' for w in at.text_input)
    assert not any(b.label=='Start' for b in at.button)

def test_returning_browser_skips_launch(monkeypatch):
    monkeypatch.setattr('launch.browser_bridge',lambda *a,**k:{'started':True,'mode':'Create account'})
    at=AppTest.from_file(str(APP)).run()
    assert any(w.label=='Username' for w in at.text_input)
    assert not any(b.label=='Start' for b in at.button)

def test_restore_requires_verified_identity():
    client=Mock();client.auth.get_user.return_value=Obj(user=None)
    auth=AuthService(client)
    assert not auth.restore_session({'access_token':'access','refresh_token':'refresh'})
    assert auth.user is None

def test_restore_in_fresh_app_service():
    client=Mock();client.auth.get_user.return_value=Obj(user=Obj(id='owner'))
    auth=AuthService(client)
    assert auth.restore_session({'access_token':'access','refresh_token':'refresh'})
    client.auth.set_session.assert_called_once_with('access','refresh')
    assert auth.user.id=='owner'

def test_malformed_session_never_contacts_provider():
    client=Mock();auth=AuthService(client)
    assert not auth.restore_session({'access_token':'access'})
    client.auth.set_session.assert_not_called()


def test_browser_user_id_does_not_authorize_resume(monkeypatch):
    monkeypatch.setattr('launch.browser_bridge',lambda *a,**k:{'started':True,'user_id':'forged','route':'edit'})
    at=AppTest.from_file(str(APP)).run()
    assert any(w.label=='Email' for w in at.text_input)
    assert not any(b.label=='Save profile' for b in at.button)

def test_restored_edit_screen_and_logout_clear_browser_tokens(monkeypatch):
    from test_ui import signed_in
    writes=[]
    def bridge(action,value=None):
        if action=='write':writes.append(value)
        return {}
    monkeypatch.setattr('launch.browser_bridge',bridge)
    at,client=signed_in()
    client.auth.get_session.return_value=Obj(access_token='access',refresh_token='refresh')
    at.run()
    assert writes[-1]['session']=={'access_token':'access','refresh_token':'refresh'}
    next(b for b in at.button if b.label=='Sign out').click().run()
    assert writes[-1]['session'] is None
    assert writes[-1]['user_id'] is None
    assert writes[-1]['started'] is True


def test_revoked_session_is_not_restored():
    client=Mock();client.auth.set_session.side_effect=Exception('revoked')
    auth=AuthService(client)
    assert not auth.restore_session({'access_token':'access','refresh_token':'refresh'})
    assert auth.user is None
    client.auth.get_user.assert_not_called()
