from datetime import date
import pytest
import google_calendar as gc


class Response:
    def __init__(self,status,data=None):self.status_code=status;self._data=data or {}
    def json(self):return self._data


class Http:
    """Records calls instead of contacting Google."""
    def __init__(self,post=None,delete=None):self.calls=[];self._post=post or (lambda *a,**k:Response(200,{'id':'g'+str(len(self.calls))}));self._delete=delete or (lambda *a,**k:Response(204))
    def post(self,url,**kwargs):
        self.calls.append(('post',url,kwargs));return self._post(url,**kwargs)
    def delete(self,url,**kwargs):
        self.calls.append(('delete',url,kwargs));return self._delete(url,**kwargs)


def test_state_is_bound_to_student_plan_kind_and_time():
    state=gc.sign_state('secret','sync','plan-1','user-a',now=1000)
    assert state.startswith(gc.STATE_PREFIX)
    assert gc.read_state('secret',state,'user-a',now=1000+gc.STATE_SECONDS-1)=={'kind':'sync','plan_id':'plan-1'}
    for bad in [lambda:gc.read_state('secret',state,'user-b',now=1000),lambda:gc.read_state('other',state,'user-a',now=1000),
                lambda:gc.read_state('secret',state,'user-a',now=1000+gc.STATE_SECONDS+1),lambda:gc.read_state('secret',state[:-2]+'xx','user-a',now=1000),
                lambda:gc.read_state('secret','sdplan.broken','user-a'),lambda:gc.read_state('secret',None,'user-a')]:
        with pytest.raises(ValueError):bad()


def test_authorization_url_asks_only_for_calendar_events_without_offline_access():
    url=gc.authorization_url('client-id','http://localhost:8501','sdplan.x')
    assert url.startswith('https://accounts.google.com/o/oauth2/v2/auth?')
    assert 'scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.events&' in url and 'access_type=online' in url
    assert 'redirect_uri=http%3A%2F%2Flocalhost%3A8501' in url and 'client-id' in url and 'secret' not in url


def test_code_exchange_returns_token_or_explains_failure():
    http=Http(post=lambda url,**k:Response(200,{'access_token':'token'}))
    assert gc.exchange_code(http,'id','secret','http://localhost:8501','code')=='token'
    assert http.calls[0][1]==gc.TOKEN_URL and http.calls[0][2]['data']['grant_type']=='authorization_code'
    with pytest.raises(ValueError,match='Nothing was changed'):gc.exchange_code(Http(post=lambda url,**k:Response(400,{'error':'invalid_grant'})),'id','secret','u','code')


def test_event_uses_local_clock_time_and_length():
    body=gc.event_body('UniArena: Winter exams (40 questions)','Finance: 40',date(2026,11,16),'09:00',15,'Europe/Lisbon')
    assert body['start']=={'dateTime':'2026-11-16T09:00:00','timeZone':'Europe/Lisbon'} and body['end']['dateTime']=='2026-11-16T09:15:00'
    assert body['summary'].startswith('UniArena') and body['description']=='Finance: 40'


def test_only_recorded_events_are_removed_and_failures_are_kept():
    http=Http(delete=lambda url,**k:Response(500 if url.endswith('/g2') else (404 if url.endswith('/g3') else 204)))
    left=gc.remove_events(http,'token',[{'uid':'a','event_id':'g1'},{'uid':'b','event_id':'g2'},{'uid':'c','event_id':'g3'}])
    assert left==[{'uid':'b','event_id':'g2'}]
    assert [c[1] for c in http.calls]==[gc.EVENTS_URL+'/g1',gc.EVENTS_URL+'/g2',gc.EVENTS_URL+'/g3']
    assert all(c[2]['headers']=={'Authorization':'Bearer token'} for c in http.calls)


def test_created_events_are_recorded_with_their_google_ids():
    replies=iter([Response(200,{'id':'g1'}),Response(403,{}),Response(200,{'id':'g3'})])
    http=Http(post=lambda url,**k:next(replies))
    created,failed=gc.add_events(http,'token',[{'uid':'a','body':{}},{'uid':'b','body':{}},{'uid':'c','body':{}}])
    assert created==[{'uid':'a','event_id':'g1'},{'uid':'c','event_id':'g3'}] and failed==1
