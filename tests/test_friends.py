from unittest.mock import Mock
from urllib.parse import urlparse, parse_qs
import pytest
from logic import normalize_friend_code, invitation_url, invitation_token
from db import FriendsRepository

def test_friend_codes_accept_optional_hash_and_case():
    assert normalize_friend_code(' #ab23cd45 ')=='AB23CD45'

@pytest.mark.parametrize('code',['','AB23','AB23CD4!','AB23CD40','AB23CD4I'])
def test_invalid_codes_are_rejected(code):
    with pytest.raises(ValueError):normalize_friend_code(code)

def test_invitation_requires_public_https_and_valid_token():
    token='a'*48
    url=invitation_url('https://studyduel-nova.streamlit.app/',token)
    assert parse_qs(urlparse(url).query)=={'invite':[token]}
    for base in ['http://localhost:8501','https://localhost','http://example.com','https://example.com@evil.test','javascript:alert(1)']:
        with pytest.raises(ValueError):invitation_url(base,token)
    with pytest.raises(ValueError):invitation_token('invalid')

def test_lookup_only_uses_normalized_code_and_no_client_identity():
    client=Mock();client.rpc.return_value.execute.return_value.data={'person':{'username':'friend'}}
    result=FriendsRepository(client).lookup(' #ab23cd45 ')
    assert result['person']['username']=='friend'
    client.rpc.assert_called_once_with('friends_action',{'p_action':'lookup','p_value':'AB23CD45'})

def test_invalid_lookup_never_contacts_provider():
    client=Mock()
    with pytest.raises(ValueError):FriendsRepository(client).lookup('bad')
    client.rpc.assert_not_called()

def test_errors_are_safe_and_not_false_success():
    client=Mock();client.rpc.return_value.execute.return_value.data={'error':'Request no longer available.'}
    with pytest.raises(ValueError,match='no longer available'):FriendsRepository(client).action('accept','test')
    client.rpc.side_effect=RuntimeError('private database credentials')
    with pytest.raises(ValueError,match='Refresh') as error:FriendsRepository(client).action('list')
    assert 'credentials' not in str(error.value)


def test_signup_confirmation_preserves_invitation():
    from auth import AuthService
    client=Mock()
    result=AuthService(client,app_url="https://studyduel-nova.streamlit.app").sign_up("student@example.com","password123","password123","student_a","a"*48)
    assert result.status=="check_email"
    assert "?invite="+"a"*48 in client.auth.sign_up.call_args.args[0]["options"]["email_redirect_to"]


def test_profile_summary_shows_studies_and_invitation_without_auto_accept(monkeypatch):
    from pathlib import Path
    from types import SimpleNamespace as Obj
    from streamlit.testing.v1 import AppTest
    from auth import AuthService
    from logic import DEFAULT_AVATAR
    profile={'username':'student_a','university':'Example University','degree':"Master's",'area':'Finance','courses':['Finance'],'languages':['English'],'avatar':DEFAULT_AVATAR,'image_mode':'Avatar'}
    monkeypatch.setattr('db.ProfileRepository.load',lambda self:profile)
    actions=[]
    def action(self,action,value=''):
        actions.append(action)
        if action=='list':return {'code':'AB23CD45','friends':[],'incoming':[],'sent':[],'invite_expires':None}
        if action=='preview_invite':return {'person':{'id':'b','username':'student_b','image_path':None}}
        return {'message':'Invitation accepted.'}
    monkeypatch.setattr('db.FriendsRepository.action',action)
    client=Mock();client.auth.get_user.return_value=Obj(user=Obj(id='a'))
    auth=AuthService(client);auth.user=client.auth.get_user.return_value.user
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=15)
    at.session_state['auth']=auth;at.query_params['invite']='a'*48
    at.run()
    assert not at.exception
    assert any('Master in Finance' in m.value for m in at.markdown)
    assert 'accept_invite' not in actions
    assert any(b.label=='Accept invitation' for b in at.button)
    next(b for b in at.button if b.label=='Accept invitation').click().run()
    assert actions.count('accept_invite')==1
    assert 'invite' not in at.query_params
    assert not at.exception
