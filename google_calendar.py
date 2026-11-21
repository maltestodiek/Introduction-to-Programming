"""Google Calendar sync for study plans. Uses a short-lived access token; nothing here stores a token."""
import base64,hashlib,hmac,json,time
from datetime import datetime,timedelta
from urllib.parse import urlencode
from uuid import NAMESPACE_URL, uuid5

AUTH_URL='https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URL='https://oauth2.googleapis.com/token'
EVENTS_URL='https://www.googleapis.com/calendar/v3/calendars/primary/events'
SCOPE='https://www.googleapis.com/auth/calendar.events'
STATE_PREFIX='sdplan.'
STATE_SECONDS=600


def _signature(secret,body):
    return base64.urlsafe_b64encode(hmac.new(secret.encode(),body.encode(),hashlib.sha256).digest()).decode().rstrip('=')


def sign_state(secret,kind,plan_id,user_id,now=None):
    """State for the Google redirect: which plan and student the answer belongs to, signed and short-lived."""
    body=base64.urlsafe_b64encode(json.dumps({'k':kind,'p':plan_id,'u':user_id,'e':int((now or time.time())+STATE_SECONDS)},separators=(',',':')).encode()).decode().rstrip('=')
    return STATE_PREFIX+body+'.'+_signature(secret,body)


def read_state(secret,state,user_id,now=None):
    """Return {'kind','plan_id'} for a valid state of this student, or raise ValueError."""
    try:
        if not state.startswith(STATE_PREFIX):raise ValueError
        body,signature=state[len(STATE_PREFIX):].split('.')
        if not hmac.compare_digest(signature,_signature(secret,body)):raise ValueError
        data=json.loads(base64.urlsafe_b64decode(body+'='*(-len(body)%4)))
        if data['u']!=user_id or data['e']<(now or time.time()) or data['k'] not in ('sync','clear'):raise ValueError
        return {'kind':data['k'],'plan_id':data['p']}
    except (ValueError,KeyError,TypeError,AttributeError):
        raise ValueError('This Google Calendar request is no longer valid. Start it again from your study plan.') from None


def authorization_url(client_id,redirect_uri,state):
    return AUTH_URL+'?'+urlencode({'client_id':client_id,'redirect_uri':redirect_uri,'response_type':'code','scope':SCOPE,'state':state,'access_type':'online','include_granted_scopes':'false','prompt':'select_account'})


def exchange_code(http,client_id,client_secret,redirect_uri,code):
    """Trade the one-time code for a short-lived access token. The token is returned, never stored."""
    response=http.post(TOKEN_URL,data={'client_id':client_id,'client_secret':client_secret,'redirect_uri':redirect_uri,'code':code,'grant_type':'authorization_code'})
    token=response.json().get('access_token') if response.status_code==200 else None
    if not token:raise ValueError('Google did not confirm the calendar permission. Nothing was changed; try again.')
    return token


def event_body(title,details,day,start_time,minutes,timezone):
    start=datetime.combine(day,datetime.strptime(start_time,'%H:%M').time());end=start+timedelta(minutes=minutes)
    return {'summary':title,'description':details,'start':{'dateTime':start.isoformat(),'timeZone':timezone},'end':{'dateTime':end.isoformat(),'timeZone':timezone},'source':{'title':'UniArena study plan','url':'https://uniarena.streamlit.app'}}


def remove_events(http,token,recorded):
    """Delete only events this app created for the plan. Returns the entries that could not be removed."""
    left=[]
    for entry in recorded:
        response=http.delete(EVENTS_URL+'/'+entry['event_id'],headers={'Authorization':'Bearer '+token})
        if response.status_code not in (200,204,404,410):left.append(entry)
    return left


def _save_event(http, headers, event):
    """Keep an existing Google ID. New sessions use the same ID across retries."""
    body = {**event['body'], 'status': 'confirmed'}
    existing = event.get('event_id')
    if existing:
        response = http.patch(f'{EVENTS_URL}/{existing}', headers=headers, json=body)
        if response.status_code not in (404, 410):
            return response

    event_id = uuid5(NAMESPACE_URL, 'https://uniarena.streamlit.app/session/' + event['uid']).hex
    response = http.post(EVENTS_URL, headers=headers, json={**body, 'id': event_id})
    if response.status_code == 409:
        # A previous insert can succeed even when its response never reaches UniArena.
        return http.patch(f'{EVENTS_URL}/{event_id}', headers=headers, json=body)
    return response


def add_events(http,token,events):
    """Return tracked IDs (including known IDs on failure) and the failed count."""
    tracked = []
    failed = 0
    headers = {'Authorization': 'Bearer ' + token}
    for event in events:
        response = _save_event(http, headers, event)
        event_id = response.json().get('id') if response.status_code in (200, 201) else None
        if not event_id:
            failed += 1
            event_id = event.get('event_id')
        if event_id:
            tracked.append({'uid': event['uid'], 'event_id': event_id})
    return tracked, failed
