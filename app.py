"""UniArena authentication and profile setup."""
import os
from pathlib import Path
from PIL import Image,ImageOps
import base64
from html import escape
import streamlit as st
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions as ClientOptions
from avatar_picker import avatar_picker
from universities import search_universities, UniversitySearchError
from auth import AuthService
from recovery import recovery_callback
from db import ProfileRepository, FriendsRepository
from launch import browser_bridge, welcome
from appearance import apply_appearance,profile_button_avatar_css
import importlib
def fresh_module(name):
    """Import a helper module, reloading it if its file changed since a long-running server loaded it."""
    module=importlib.import_module(name)
    if getattr(module,"_file_stamp",None)!=Path(module.__file__).stat().st_mtime:module=importlib.reload(module)
    return module
fresh_module("course_catalog")
from course_catalog import course_options,field_options,load_universities,load_university_courses,match_courses
from sharing import share_invitation
from answer_order import display_options
from logic import normalize_friend_code, invitation_url, invitation_token
from logic import CATALOG, LANGUAGES, DEFAULT_AVATAR, OPTIONS, DEGREES, render_avatar, crop_photo, validate_username, xp_breakdown

LOGO_PATH=Path(__file__).parent / "assets" / "uniarena-icon.png"
# The logo is wider than tall; the browser-tab icon needs a square, so pad it with transparency.
st.set_page_config(page_title="UniArena",page_icon=ImageOps.pad(Image.open(LOGO_PATH).convert("RGBA"),(256,256),color=(0,0,0,0)),layout="centered")
apply_appearance()
st.markdown("""<style>
.block-container{max-width:940px;padding-top:2.5rem}
[data-testid="stCaptionContainer"]{opacity:1!important;color:var(--sd-muted)!important}
[data-testid="stPopoverBody"] [data-testid="stCaptionContainer"]{color:inherit!important}
h1{letter-spacing:-.04em}div[data-testid="stForm"]{border-radius:18px;padding:24px}
.stButton>button{border-radius:10px}div[data-testid="stMetric"]{background:var(--sd-surface);color:var(--sd-text);border:1px solid var(--sd-border);border-radius:16px;padding:20px;border-top:4px solid #6EE7B7}
.sd-xp-summary{background:var(--sd-surface);border:1px solid var(--sd-border);border-radius:16px;border-top:4px solid #6EE7B7;padding:20px;min-height:126px}.sd-xp-summary__label{font-size:1rem;font-weight:500}.sd-xp-summary__total{font-size:2.6rem;font-weight:600;line-height:1.15;margin:14px 0}.sd-xp-summary__breakdown{font-size:.92rem;line-height:1.35}.sd-xp-summary__game{color:#7C3AED}.sd-xp-summary__creator{color:#047857}
</style>""",unsafe_allow_html=True)
st.html('<style>'+(Path(__file__).parent/'assets'/'navigation.css').read_text()+'</style>')
import time
page_speed=fresh_module("page_speed")
logo_copies=page_speed.logo_variants(str(LOGO_PATH),LOGO_PATH.stat().st_mtime)
logo_data=logo_copies["medium"]   # welcome screen
logo_small=logo_copies["small"]   # header and sign-in
# The invitation remains in the URL across signup, email confirmation and login.
if "invite" in st.query_params:
    try:st.session_state.pending_invite=invitation_token(st.query_params["invite"])
    except ValueError:
        st.session_state.pop("pending_invite",None)
        st.warning("This invitation link is invalid. Ask your friend for a new one.")

def portrait(data,size=160):
    encoded=base64.b64encode(data).decode()
    st.html(f'<img src="data:image/png;base64,{encoded}" alt="Profile picture" style="width:{size}px;height:{size}px;max-width:100%;object-fit:cover;border-radius:50%;display:block;background:var(--sd-avatar)" />')

def public_person(person,repo):
    left,right=st.columns([1,5])
    with left:
        try: data=repo.image(person.get("image_path"))
        except Exception:data=None
        portrait(data or render_avatar(DEFAULT_AVATAR),56)
    with right:st.write(person["username"])

def chat_call(client,action,data=None,quiet=False):
    from db import ChatRepository
    try:return ChatRepository(client).action(action,data)
    except ValueError as exc:
        if not quiet:st.error(str(exc))
        return None


def open_private_chat(client,user_id):
    result=chat_call(client,'open',{'user_id':user_id})
    if result is not None:
        st.session_state.chat_open=result['id'];st.rerun()


def session_partner_chat(client,kind,session_id,location='round'):
    data=chat_call(client,'partner',{'kind':kind,'id':session_id},quiet=True)
    if not data or not data.get('partner'):return
    person=data['partner']
    with st.popover(person['username'],icon=':material/person:'):
        public_person(person,ProfileRepository(client,st.session_state.auth.user.id))
        if st.button('Send friend request',icon=':material/person_add:',key=f'friend_partner_{location}_{kind}_{session_id}'):
            result=friend_action(FriendsRepository(client),'request_user',person['id'])
            if result:st.success(result.get('message','Friend request sent.'))
        if st.button('Send message',icon=':material/chat:',key=f'chat_partner_{location}_{kind}_{session_id}'):
            open_private_chat(client,person['id'])


@st.fragment(run_every='15s')
def chat_dropdown(client):
    # Unmount the inbox popover so its portal cannot cover the conversation.
    if st.session_state.get('chat_open'):
        st.button('Chats',icon=':material/chat:',disabled=True,use_container_width=True)
        return
    data=chat_call(client,'list',quiet=True)
    threads=data['threads'] if data else []
    unread=sum(t['unread'] for t in threads)
    with st.popover('Chats'+(f' ({unread})' if unread else ''),icon=':material/chat:',use_container_width=True):
        if data is None:st.caption('Chats are temporarily unavailable. Please try again.')
        elif not threads:st.caption('No conversations yet. Click a Battle or Study partner’s name to send a message.')
        for thread in threads:
            with st.container(border=True):
                pic,details=st.columns([1,5])
                with pic:
                    try:photo=ProfileRepository(client,st.session_state.auth.user.id).image(thread.get('image_path'))
                    except Exception:photo=None
                    portrait(photo or render_avatar(DEFAULT_AVATAR),40)
                with details:
                    st.text(thread['username'])
                    st.text(('You: ' if thread.get('from_me') else '')+thread['preview'])
                    if thread['unread']:st.caption(f"{thread['unread']} unread")
                if st.button('Open chat with '+thread['username'],key='chat_open_'+thread['id'],icon=':material/forum:'):
                    st.session_state.chat_open=thread['id'];st.rerun()


def dismiss_chat():
    st.session_state.pop('chat_open',None)


@st.dialog('Chat',width='large',on_dismiss=dismiss_chat,icon=':material/chat:')
def private_chat_dialog(client,thread_id,own_picture=None):
    st.html('<span class="sd-chat-marker"></span><style>'+(Path(__file__).parent/'assets'/'chat.css').read_text()+'</style>')
    chat_conversation(client,thread_id,own_picture)


@st.fragment(run_every='3s')
def chat_conversation(client,thread_id,own_picture=None):
    from uuid import uuid4
    data=chat_call(client,'read',{'id':thread_id})
    if data is None:return
    image_repo=ProfileRepository(client,st.session_state.auth.user.id)
    identity,friend_controls=st.columns([3,2],vertical_alignment='center')
    with identity:public_person(data['partner'],image_repo)
    with friend_controls:
        friends=FriendsRepository(client)
        try:relationships=friends.action('list')
        except ValueError:relationships=None
        peer=data['partner']['id']
        if relationships is None:st.caption('Friend status unavailable.')
        elif any(e['person']['id']==peer for e in relationships.get('friends',[])):
            st.caption('Friends')
        elif any(e['person']['id']==peer for e in relationships.get('sent',[])):
            st.caption('Friend request sent')
        else:
            incoming=next((e for e in relationships.get('incoming',[]) if e['person']['id']==peer),None)
            label='Accept friend request' if incoming else 'Send friend request'
            if st.button(label,icon=':material/person_add:',key='chat_friend_'+thread_id):
                result=friend_action(friends,'accept' if incoming else 'request_user',incoming['id'] if incoming else peer)
                if result:st.rerun()
    try:partner_picture=image_repo.image(data['partner'].get('image_path'))
    except Exception:partner_picture=None
    def avatar_url(raw):
        return 'data:image/png;base64,'+base64.b64encode(raw or render_avatar(DEFAULT_AVATAR)).decode()
    own_avatar=avatar_url(own_picture)
    partner_avatar=avatar_url(partner_picture)
    st.caption('Private conversation · Updates every few seconds. A Battle timer keeps running while you chat.')
    history_key='chat_history_'+thread_id
    history={m['id']:m for m in st.session_state.get(history_key,[])}
    history.update({m['id']:m for m in data['messages']})
    messages=sorted(history.values(),key=lambda m:m['id'])
    st.session_state[history_key]=messages
    older_key='chat_older_'+thread_id
    if older_key not in st.session_state:st.session_state[older_key]=data['has_older']
    if st.session_state[older_key] and messages and st.button('Load earlier messages',key='chat_earlier_'+thread_id):
        older=chat_call(client,'read',{'id':thread_id,'before':messages[0]['id']})
        if older is not None:
            history.update({m['id']:m for m in older['messages']})
            st.session_state[history_key]=sorted(history.values(),key=lambda m:m['id'])
            st.session_state[older_key]=older['has_older'];st.rerun()
    with st.container(height=340,border=True,autoscroll=True,key="chat_messages"):
        if not messages:st.caption('Start the conversation. Only you and this person can read it.')
        for message in messages:
            with st.chat_message('You' if message['from_me'] else data['partner']['username'],avatar=own_avatar if message['from_me'] else partner_avatar):
                st.text(message['body']);st.caption(('You' if message['from_me'] else data['partner']['username'])+' · '+message['created_at'][:16].replace('T',' ')+' UTC')
    if data['messages']:
        latest=data['messages'][-1]['id'];seen_key='chat_seen_'+thread_id
        if st.session_state.get(seen_key)!=latest and chat_call(client,'seen',{'id':thread_id,'through':latest},quiet=True) is not None:st.session_state[seen_key]=latest
    text_key='chat_text_'+thread_id
    if st.session_state.pop('chat_clear_'+thread_id,False):st.session_state[text_key]=''
    with st.form('chat_send_'+thread_id):
        text=st.text_area('Message',key=text_key,max_chars=2000,height=80,placeholder='Write a message…')
        send=st.form_submit_button('Send message',icon=':material/send:',type='primary')
    if send:
        body=text.strip()
        if not body:st.warning('Write a message before sending.');return
        pending_key='chat_pending_'+thread_id
        pending=st.session_state.get(pending_key)
        if not pending or pending['body']!=body:
            pending={'id':thread_id,'body':body,'request_id':str(uuid4())};st.session_state[pending_key]=pending
        result=chat_call(client,'send',pending)
        if result is not None:
            st.session_state.pop(pending_key,None);st.session_state['chat_clear_'+thread_id]=True;st.rerun()


def friend_action(friends,action,value=""):
    try:
        result=friends.action(action,value)
        st.session_state.notice=result.get("message","Updated.")
        return result
    except ValueError as exc:
        st.error(str(exc))
        return None

def open_friend_match(person,mode):
    """Open the existing match setup with a friend already selected."""
    st.session_state.main_page='Play'
    if mode=='battle':
        st.session_state.play_mode_preview='Battle'
        st.session_state.battle_new_setup=True
        st.session_state.battle_invite_friend=person
    else:
        st.session_state.play_mode_preview='Study'
        st.session_state.study_active=True
        st.session_state.study_choice='Study together'
        st.session_state.study_partner='Friend'
        st.session_state.study_invite_friend=person
    st.rerun()


def friend_match_row(item,repo,friends):
    # Keep every frequent friend action visible instead of hiding it in a menu.
    person=item["person"]
    avatar,profile,battle,study,remove=st.columns([0.7,1.55,2.25,1.65,1.45],vertical_alignment="center")
    with avatar:
        try: data=repo.image(person.get("image_path"))
        except Exception:data=None
        portrait(data or render_avatar(DEFAULT_AVATAR),48)
    with profile:
        if st.button(person["username"],key="friend_chat_"+item["id"],icon=":material/chat:",help="Open chat with "+person["username"]):
            open_private_chat(friends.client,person["id"])
    with battle:
        if st.button('Challenge to a Battle',key='friend_battle_'+item['id'],use_container_width=True):
            open_friend_match(person,'battle')
    with study:
        if st.button('Study together',key='friend_study_'+item['id'],use_container_width=True):
            open_friend_match(person,'study')
    with remove:
        if st.button('Remove friend',key='remove_friend_'+item['id'],use_container_width=True):
            st.session_state.friend_remove_confirm=item['id'];st.rerun()
    if st.session_state.get('friend_remove_confirm')==item['id']:
        st.warning(f"Remove {person['username']} as a friend? This removes the friendship for both of you.")
        confirm,cancel=st.columns(2)
        if confirm.button('Confirm removal',key='remove_'+item['id'],type='primary'):
            if friend_action(friends,'remove',item['id']):
                st.session_state.pop('friend_remove_confirm',None);st.rerun()
        if cancel.button('Keep friend',key='keep_friend_'+item['id']):
            st.session_state.pop('friend_remove_confirm',None);st.rerun()

def friends_screen(friends,repo,state):
    if st.session_state.get('study_return_after_friends'):
        if st.button('Back to Study Together',icon=':material/arrow_back:'):
            st.session_state.pop('study_return_after_friends',None)
            st.session_state.main_page='Play';st.session_state.study_active=True;st.session_state.study_choice='Study together';st.rerun()
    st.caption("Your friend code")
    st.code("#"+state["code"],language=None)
    st.caption("Share this code so another student can send you a request. It is not a login code.")
    if st.button("Refresh friends"):st.rerun()
    token=st.session_state.get("pending_invite")
    if token:
        st.subheader("Friend invitation")
        try:
            invitation_token(token)
            preview=friends.action("preview_invite",token)
            public_person(preview["person"],repo)
            st.write("Accept this invitation to add each other as friends.")
            if st.button("Accept invitation",type="primary"):
                if friend_action(friends,"accept_invite",token):
                    st.session_state.pop("pending_invite",None)
                    if "invite" in st.query_params:del st.query_params["invite"]
                    st.rerun()
        except ValueError as exc:st.warning(str(exc))
        if st.button("Dismiss invitation"):
            st.session_state.pop("pending_invite",None)
            if "invite" in st.query_params:del st.query_params["invite"]
            st.rerun()
    st.subheader("Add a friend by code")
    with st.form("find_friend"):
        code=st.text_input("Friend code",placeholder="#AB23CD45",max_chars=12)
        find=st.form_submit_button("Find friend")
    if find:
        st.session_state.pop("friend_preview",None)
        try:
            normalized=normalize_friend_code(code)
            result=friends.lookup(normalized)
            st.session_state.friend_preview={"code":normalized,"person":result["person"]}
        except ValueError as exc:st.error(str(exc))
    preview=st.session_state.get("friend_preview")
    if preview:
        public_person(preview["person"],repo)
        if st.button("Send friend request"):
            if friend_action(friends,"request",preview["code"]):
                st.session_state.pop("friend_preview",None)
                st.rerun()
    st.subheader("Find students at your university")
    try:university_directory=friends.university_profiles()
    except ValueError as exc:st.error(str(exc));university_directory={'profiles':[]}
    students=university_directory['profiles']
    if students:
        st.caption(f"Students with a profile at {university_directory['university']}.")
        for student in students:
            with st.container(border=True):
                avatar,name,university,action=st.columns([0.6,2.4,4.2,1.8],vertical_alignment="center")
                with avatar:
                    try:data=repo.image(student.get("image_path"))
                    except Exception:data=None
                    portrait(data or render_avatar(DEFAULT_AVATAR),48)
                with name:st.write("**"+student['username']+"**")
                with university:st.caption(university_directory['university'])
                with action:
                    if st.button("Add as friend",key="university_friend_"+student['id'],use_container_width=True):
                        try:
                            result=friends.request_university_friend(student['id'])
                            st.session_state.notice=result.get('message','Friend request sent.');st.rerun()
                        except ValueError as exc:st.error(str(exc))
    else:st.caption("No other students from your university are available to add right now.")
    st.subheader("Invite a friend with a link")
    if st.button("Create new invitation link"):
        result=friend_action(friends,"create_invite")
        if result:
            st.session_state.share_invite_token=result["token"]
            st.rerun()
    if state.get("invite_expires"):
        if not st.session_state.get("share_invite_token"):
            st.caption("Your existing link still works. Create a new link if you need another copy; this replaces the old one.")
        if st.button("Revoke invitation link"):
            if friend_action(friends,"revoke_invite"):
                st.session_state.pop("share_invite_token",None)
                st.rerun()
    st.caption("Links expire after seven days. Creating a new link replaces the previous one.")
    if token:=st.session_state.get("share_invite_token"):
        st.subheader("Your invitation link")
        try:share_invitation(invitation_url(config("PUBLIC_APP_URL") or config("APP_URL") or "http://localhost:8501",token))
        except ValueError as exc:st.info(str(exc))
    empty_messages={"Incoming requests":":material/inbox: No Incoming request","Sent requests":"Connect with your friends and Battle them","Your friends":"Nothing here yet."}
    for title,items,actions in [("Incoming requests",state["incoming"],[("Accept","accept"),("Decline","decline")]),("Sent requests",state["sent"],[("Cancel request","cancel")]),("Your friends",state["friends"],[])]:
        st.subheader(title)
        if not items:st.caption(empty_messages[title])
        for item in items:
            with st.container(border=True):
                if title=="Your friends":friend_match_row(item,repo,friends)
                else:public_person(item["person"],repo)
                for label,action in actions:
                    if st.button(label,key=action+"_"+item["id"]):
                        if friend_action(friends,action,item["id"]):st.rerun()

def calculator_input_changed(key):
    st.session_state.pop(key+'_result',None)
    st.session_state.pop(key+'_error',None)


def calculator_rules():
    # A long-running server can still hold logic.py from before a deploy; reload it once so rounding applies.
    import importlib,logic
    return logic if hasattr(logic,'CALCULATOR_DECIMALS') else importlib.reload(logic)


def calculator_key(key,token):
    calculate=calculator_rules().calculate
    calculator_input_changed(key)
    value=st.session_state.get(key,'')
    if token=='Clear':
        st.session_state[key]='';st.session_state.pop(key+'_result',None)
    elif token=='⌫':st.session_state[key]=value[:-1]
    elif token=='=':
        try:st.session_state[key+'_result']=calculate(value)
        except ValueError as exc:st.session_state[key+'_error']=str(exc)
    elif len(value)<120:st.session_state[key]=value+('sqrt(' if token=='√' else token)


def clear_notepads():
    for k in [k for k in st.session_state if str(k).startswith('notepad_') and not str(k).endswith(('_toggle','_close'))]:st.session_state.pop(k,None)


def notepad_rules():
    # A long-running server can still hold logic.py from before a deploy; reload it once instead of failing.
    import importlib,logic
    return logic if hasattr(logic,'scratch_note') else importlib.reload(logic)


def notepad_changed(key):
    st.session_state[key+'_text']=notepad_rules().scratch_note(st.session_state.get(key,''))


def question_tools(identity,allow_calculator):
    if st.session_state.get('notepad_question')!=identity:
        clear_notepads();st.session_state['notepad_question']=identity
    calc='calculator_open_'+identity;note='notepad_open_'+identity
    st.html('<style>'+ (Path(__file__).parent/'assets'/'question-tools.css').read_text()+'</style>')
    with st.container(horizontal=True,key='question_tools_bar'):
        if allow_calculator and st.button('Close calculator' if st.session_state.get(calc) else 'Calculator',icon=':material/calculate:',key=calc+'_toggle'):
            st.session_state[calc]=not st.session_state.get(calc,False);st.rerun()
        if st.button('Close notepad' if st.session_state.get(note) else 'Notepad',icon=':material/edit_note:',key='notepad_'+identity+'_toggle'):
            st.session_state[note]=not st.session_state.get(note,False);st.rerun()
    show_calculator=allow_calculator and st.session_state.get(calc);show_notepad=st.session_state.get(note)
    if show_calculator or show_notepad:
        with st.container(key='question_tools_panel'):
            if show_calculator:question_calculator(identity)
            if show_notepad:question_notepad(identity)


@st.fragment
def question_notepad(identity):
    key='notepad_'+identity
    with st.container(border=True,key='notepad_panel'):
        title,close=st.columns([2,1])
        title.markdown('**:material/edit_note: Notepad**')
        if close.button('Close',icon=':material/close:',key=key+'_close'):
            st.session_state['notepad_open_'+identity]=False;st.rerun()
        if key not in st.session_state:st.session_state[key]=st.session_state.get(key+'_text','')
        st.text_area('Notes',key=key,max_chars=notepad_rules().NOTEPAD_LIMIT,height=96,placeholder='Scratch notes for this question. Not saved.',label_visibility='collapsed',on_change=notepad_changed,args=(key,))


@st.fragment
def question_calculator(identity):
    key='calculator_'+identity
    st.html('<style>'+ (Path(__file__).parent/'assets'/'calculator.css').read_text()+'</style>')
    with st.container(border=True,key='calculator_panel'):
        title,close=st.columns([2,1])
        title.markdown('**:material/calculate: Calculator**')
        if close.button('Close',icon=':material/close:',key=key+'_close'):
            st.session_state['calculator_open_'+identity]=False;st.rerun()
        st.text_input('Calculation',key=key,max_chars=120,placeholder='e.g. (100 + 20) ÷ 4',label_visibility='collapsed',on_change=calculator_input_changed,args=(key,))
        result=st.session_state.get(key+'_result','—')
        decimals=calculator_rules().CALCULATOR_DECIMALS
        st.html(f'<div style="text-align:right;padding:4px 0 12px;font-size:1.8rem;font-weight:700;overflow-wrap:anywhere"><span style="display:block;font-size:.8rem;font-weight:400;opacity:.7">Result</span>{escape(result)}<span style="display:block;font-size:.75rem;font-weight:400;opacity:.7">Rounded to {decimals} decimal places</span></div>')
        for row in [('Clear','⌫','(',')'),('7','8','9','÷'),('4','5','6','×'),('1','2','3','−'),('0','.','√','^'),('+','=')]:
            for col,token in zip(st.columns(len(row)),row):
                label={'Clear':'C','^':'xʸ'}.get(token,token)
                col.button(label,key=key+'_'+token,help={'Clear':'Clear calculation','√':'Square root: √ inserts sqrt(. Close the bracket before calculating.','^':'Power: enter a whole-number exponent from −12 to 12.'}.get(token),type='secondary' if token.isdigit() or token=='.' else 'primary',on_click=calculator_key,args=(key,token),use_container_width=True)
        if st.session_state.get(key+'_error'):st.error(st.session_state[key+'_error'])


def deck_input_changed(card_id,field,key,answer_index=None):
    draft=st.session_state.deck_draft
    st.session_state.pop('deck_review',None)
    if card_id is None:draft[field]=st.session_state[key];return
    card=next(c for c in draft['cards'] if c['id']==card_id)
    if answer_index is None:card[field]=st.session_state[key]
    else:card['answers'][answer_index]['text']=st.session_state[key]


def deck_select_card(index):
    st.session_state.deck_index=index


def show_deck_cards(cards):
    for i,card in enumerate(cards):
        with st.container(border=True):
            st.subheader(f"Question {i+1}")
            st.write(card['question'])
            st.caption('Calculator allowed' if card.get('allow_calculator',False) else 'Calculator not allowed')
            for n,a in enumerate(card['answers']):
                if a['id']==card['correct_answer_id']:st.success(f"{chr(65+n)}. {a['text']} — Correct answer")
                else:st.write(f"{chr(65+n)}. {a['text']}")


@st.dialog('Choose exactly 15 questions')
def battle_card_selection_dialog(count):
    st.error(f'You selected {count} questions. A Battle Deck must contain exactly 15 questions.')
    if st.button('Continue selecting',type='primary'):
        st.rerun()


def battle_deck_creator(client):
    """Choose a reviewed Study deck and freeze exactly 15 questions for Battle."""
    from db import BattleRepository
    repository=BattleRepository(client)
    st.header('Create Battle Mode Deck')
    if st.session_state.get('battle_return_study'):
        if st.button('Back to Study deck',icon=':material/arrow_back:'):
            for key in ('battle_deck_creator','battle_source_id','battle_return_study'):st.session_state.pop(key,None)
            st.rerun()
    st.caption('Choose 15 questions from one of your reviewed Study decks. After submission, the snapshot can be played by everyone.')
    try:data=repository.action('sources')
    except ValueError as exc:st.error(str(exc));return
    sources=data.get('sources',[])
    if not sources:
        st.info('Create and save a reviewed Study deck first.');return
    labels={source['id']:f"{source['name']} · {source['course']} · {source['language']} · {source['count']} questions" for source in sources}
    preselected=st.session_state.get('battle_source_id')
    source_id=st.selectbox('Source Study deck',list(labels),format_func=labels.get,index=list(labels).index(preselected) if preselected in labels else None,placeholder='Choose one of your Study decks')
    if source_id is None:
        st.info('Choose a Study deck to see its questions.')
        return
    source=next(item for item in sources if item['id']==source_id)
    if not source.get('battle_capable'):
        st.warning('This deck is not Battle-capable yet. It needs at least 15 complete questions.');return
    try:deck=repository.action('source',{'id':source_id})
    except ValueError as exc:st.error(str(exc));return
    st.subheader('Choose exactly 15 questions')
    selected=[]
    for number,card in enumerate(deck['cards'],1):
        if st.checkbox(f"{number}. {card['question']}",key='battle_card_'+source_id+'_'+card['id']):selected.append(card['id'])
    st.caption(f'{len(selected)} of 15 questions selected.')
    name=st.text_input('Battle Deck name',value=deck['name'],max_chars=120)
    consent=st.checkbox('By submitting, you accept that the deck can be played by everyone.')
    if st.button('Submit Battle Deck',type='primary'):
        if len(selected)!=15:
            battle_card_selection_dialog(len(selected))
        elif not consent:
            st.error('Accept that the deck can be played by everyone before submitting.')
        else:
            try:created=repository.action('create_deck',{'source_deck_id':source_id,'card_ids':selected,'name':name,'consent':consent})
            except ValueError as exc:st.error(str(exc))
            else:
                st.success('Your public 15-question Battle Deck is ready.')
                for key in ('battle_deck_creator','battle_source_id','battle_return_study'):st.session_state.pop(key,None)
                st.session_state.battle_deck_created=created['id'];st.rerun()


def decks_screen(client,profile):
    from db import DeckRepository,AnkiImportRepository
    from logic import new_deck,validate_card,validate_deck,add_card,delete_card
    repository=DeckRepository(client)
    st.title('Decks')
    if st.session_state.get('battle_deck_creator'):
        battle_deck_creator(client);return
    if st.session_state.get('anki_import_open'):
        anki_import_screen(client,profile)
        return
    if st.session_state.get('pdf_import_open'):
        pdf_import_screen(client,profile)
        return
    if st.session_state.get('anki_generation_open'):
        anki_generation_screen(client,profile)
        return
    if st.session_state.get('study_library'):
        study_library(client,profile);return
    if st.session_state.get('deck_open'):
        if st.button('Back to course decks'):
            st.session_state.pop('deck_open',None);st.rerun()
        try:deck=repository.get(st.session_state.deck_open)
        except ValueError as exc:st.error(str(exc));return
        st.caption(f"Decks › {deck['course']} › {deck['name']}")
        st.header(deck['name'])
        st.caption(f"By {(deck.get('profiles') or {}).get('username','Student')} · 15 questions · Not rated")
        st.caption('Deck language: '+(deck.get('language') or 'Not set'))
        if not deck.get('language') and deck.get('creator_id')==st.session_state.auth.user.id:
            language=st.selectbox('Set missing deck language',profile['languages'])
            st.caption('This can only be set once. Your questions and answers remain unchanged.')
            if st.button('Save deck language'):
                from db import PlayRepository
                if play_request(PlayRepository(client),'set_language',{'deck_id':deck['id'],'language':language}) is not None:st.rerun()
        st.info('Published decks are read-only. All solutions are shown for studying.')
        show_deck_cards(deck['cards']);return
    if 'deck_draft' in st.session_state:
        draft=st.session_state.deck_draft
        review=st.session_state.get('deck_review')
        if review:
            st.caption(f"Decks › {draft['course']} › Review")
            st.header(draft['name'])
            st.warning('Check all 15 questions and solutions. Once published, this deck cannot be edited or deleted.')
            show_deck_cards(draft['cards'])
            back,confirm=st.columns(2)
            if back.button('Back to editing',use_container_width=True):
                st.session_state.pop('deck_review',None);st.rerun()
            if confirm.button('Create Deck',type='primary',use_container_width=True):
                try:result=repository.publish(draft,review)
                except ValueError as exc:st.error(str(exc));return
                st.session_state.deck_open=result['id']
                st.session_state.deck_course=draft['course']
                st.session_state.pop('deck_draft',None);st.session_state.pop('deck_review',None)
                st.session_state.notice='Your deck is published.';st.rerun()
            return
        st.caption('Decks › Create New Deck › Manual')
        st.info('Your draft stays while you navigate in this session. Publish it before closing or refreshing the page.')
        courses=profile['courses']
        course_key='deck_course_'+draft['id'];name_key='deck_name_'+draft['id']
        st.selectbox('Course',courses,index=courses.index(draft['course']) if draft['course'] in courses else 0,key=course_key,on_change=deck_input_changed,args=(None,'course',course_key))
        if draft['course'] not in courses:draft['course']=courses[0]
        language_key='deck_language_'+draft['id']
        if draft.get('language') not in profile['languages']:
            draft['language']=profile['languages'][0];st.session_state.pop('deck_review',None)
        st.selectbox('Deck language',profile['languages'],index=profile['languages'].index(draft['language']),key=language_key,on_change=deck_input_changed,args=(None,'language',language_key))
        st.text_input('Deck name',value=draft['name'],key=name_key,on_change=deck_input_changed,args=(None,'name',name_key),placeholder='For example: Corporate Finance foundations')
        completed=[]
        for c in draft['cards']:
            try:validate_card(c);completed.append(True)
            except ValueError:completed.append(False)
        st.progress(sum(completed)/15,text=f'{sum(completed)} of 15 cards complete')
        st.caption('Choose any card to edit it. Completed cards show a check icon.')
        for row in range(0,len(draft['cards']),5):
            columns=st.columns(5)
            for j in range(row,min(row+5,len(draft['cards']))):
                columns[j-row].button(str(j+1),icon=':material/check_circle:' if completed[j] else ':material/radio_button_unchecked:',key='choose_'+draft['cards'][j]['id'],on_click=deck_select_card,args=(j,),use_container_width=True)
        index=min(st.session_state.get('deck_index',0),len(draft['cards'])-1)
        card=draft['cards'][index];prefix='deck_card_'+card['id']
        st.subheader(f'Card {index+1} of 15')
        st.text_area('Question',value=card['question'],key=prefix+'_q',on_change=deck_input_changed,args=(card['id'],'question',prefix+'_q'))
        for i,a in enumerate(card['answers']):
            key=prefix+'_answer_'+a['id']
            st.text_input(f'Answer {i+1}',value=a['text'],key=key,on_change=deck_input_changed,args=(card['id'],'answers',key,i))
        answer_ids=[a['id'] for a in card['answers']]
        st.radio('Correct answer',answer_ids,index=answer_ids.index(card['correct_answer_id']) if card['correct_answer_id'] in answer_ids else None,format_func=lambda value:f'Answer {answer_ids.index(value)+1}',horizontal=True,key=prefix+'_correct',on_change=deck_input_changed,args=(card['id'],'correct_answer_id',prefix+'_correct'))
        st.checkbox('Allow calculator for this question',value=card.get('allow_calculator',False),key=prefix+'_calculator',on_change=deck_input_changed,args=(card['id'],'allow_calculator',prefix+'_calculator'))
        a,b=st.columns(2)
        if a.button('+ Add Flashcard',disabled=len(draft['cards'])>=15,use_container_width=True):
            try:st.session_state.deck_draft=add_card(draft,index)
            except ValueError as exc:st.error(str(exc))
            else:st.session_state.deck_index=len(draft['cards']);st.rerun()
        if b.button('Delete this card',use_container_width=True):
            st.session_state.deck_draft=delete_card(draft,index)
            st.session_state.deck_index=max(0,index-1);st.session_state.pop('deck_review',None);st.rerun()
        error=None
        try:validate_deck(draft)
        except ValueError as exc:error=str(exc)
        if error:st.caption(error)
        if st.button('Save Deck',type='primary',disabled=error is not None,use_container_width=True):
            try:st.session_state.deck_review=repository.review(draft)
            except ValueError as exc:st.error(str(exc))
            else:st.rerun()
        with st.expander('Discard draft'):
            st.caption('This removes the unpublished draft from this session.')
            if st.button('Confirm discard'):
                st.session_state.pop('deck_draft',None);st.session_state.pop('deck_review',None);st.rerun()
        return
    assets=Path(__file__).parent/'assets'
    st.html('<style>'+''.join((assets/name).read_text() for name in ('deck-creation.css','course-list.css'))+'</style>')
    st.subheader('Create a deck')
    st.caption('Choose how you want to create your next set of questions.')
    manual,anki,ai=st.columns(3)
    with manual:
        with st.container(border=True,key='deck_create_manual'):
            st.markdown('<div class="deck-create-icon">+</div>',unsafe_allow_html=True)
            st.markdown('#### Manual deck')
            st.caption('Write questions from scratch and organise them into lectures.')
            with st.popover('Create deck',type='primary',use_container_width=True):
                if st.button('Create Study Deck',use_container_width=True):
                    st.session_state.study_library=True
                    if not st.session_state.get('study_draft'):
                        st.session_state.study_draft=new_deck(profile['courses'][0],profile['languages'][0]);st.session_state.study_revision=0
                    st.session_state.pop('study_deck_open',None);st.rerun()
                if st.button('Create Battle Mode Deck',use_container_width=True):
                    st.session_state.pop('battle_source_id',None);st.session_state.pop('battle_return_study',None)
                    st.session_state.battle_deck_creator=True;st.rerun()
    with anki:
        with st.container(border=True,key='deck_create_anki'):
            st.markdown('<div class="deck-create-icon">▤</div>',unsafe_allow_html=True)
            st.markdown('#### AI Anki import')
            st.caption('Import Anki cards, then review AI-generated questions.')
            if st.button('Import Anki deck',use_container_width=True):
                st.session_state.anki_import_open=True;st.session_state.pop('anki_import_result',None);st.rerun()
    with ai:
        with st.container(border=True,key='deck_create_slides'):
            st.markdown('<div class="deck-create-icon">✦</div>',unsafe_allow_html=True)
            st.markdown('#### AI from lecture slides')
            st.caption('Upload text-based PDF slides, then review generated questions.')
            if st.button('Generate with AI',use_container_width=True):st.session_state.pdf_import_open=True;st.session_state.pop('pdf_import_result',None);st.rerun()
    st.divider()
    course_names=list(dict.fromkeys(profile['courses']))
    from db import BattleRepository
    # Battle Mode decks live in battle_decks; the old decks table only holds retired classic duel decks.
    try:battle_decks=BattleRepository(client).catalog()
    except ValueError as exc:battle_decks=[];st.warning(str(exc))
    public_study=study_public_request(client,'list')
    if public_study is None:return
    course_keys={course.strip().casefold() for course in course_names}
    study_decks=[deck for deck in public_study.get('decks',[]) if deck.get('course','').strip().casefold() in course_keys]
    battle_by_course={course.strip().casefold():[] for course in course_names}
    study_by_course={course.strip().casefold():[] for course in course_names}
    for deck in battle_decks:battle_by_course.setdefault(deck.get('course','').strip().casefold(),[]).append(deck)
    for deck in study_decks:study_by_course.setdefault(deck.get('course','').strip().casefold(),[]).append(deck)

    course_heading,review_action=st.columns([5,1],vertical_alignment='center')
    with course_heading:
        st.subheader('Your courses')
        st.caption('Choose a course to study at your pace or start a Battle.')
    with review_action:
        if st.button('Daily review',key='open_daily_review',icon=':material/local_fire_department:',use_container_width=True):
            st.session_state.study_library=True;st.rerun()
    for index,course in enumerate(course_names):
        course_key=course.strip().casefold()
        study_count=len(study_by_course.get(course_key,[]))
        battle_count=len(battle_by_course.get(course_key,[]))
        with st.container(border=True,key='course_list_'+str(index)):
            summary,availability,actions=st.columns([2.2,1.5,2.3],vertical_alignment='center')
            with summary:
                st.markdown('#### '+course)
                total=study_count+battle_count
                st.caption(f"{total} deck{'s' if total!=1 else ''} available")
            with availability:
                st.markdown(f'<div class="course-list-count"><strong>{study_count}</strong><span>Study decks</span><strong>{battle_count}</strong><span>Battle decks</span></div>',unsafe_allow_html=True)
            with actions:
                study_action,battle_action=st.columns(2)
                if study_action.button('Study',key='course_study_'+str(index),icon=':material/menu_book:',use_container_width=True):
                    st.session_state.study_library=True;st.rerun()
                if battle_action.button('Battle',key='course_battle_'+str(index),icon=':material/swords:',use_container_width=True):
                    st.session_state.main_page='Play';st.session_state.play_mode_preview='Battle';st.session_state.battle_new_setup=True
                    st.session_state.battle_course=course;st.session_state.battle_language=profile['languages'][0]
                    st.rerun()
            course_decks=[('study',deck) for deck in study_by_course.get(course_key,[])]+[('battle',deck) for deck in battle_by_course.get(course_key,[])]
            with st.expander(f'Decks in this course ({len(course_decks)})'):
                if not course_decks:st.caption(f'No decks in {course} yet. Create the first one above.')
                for kind,deck in course_decks:
                    info,action=st.columns([3,1],vertical_alignment='center')
                    info.markdown((':material/menu_book:' if kind=='study' else ':material/swords:')+' **'+deck['name']+'**')
                    info.caption(course_deck_meta(kind,deck))
                    with action:course_deck_action(client,kind,deck,f'course_menu_{index}_{kind}_{deck["id"]}',compact=True)

    st.subheader('Your decks')
    filter_choice=st.segmented_control('Deck filter',['All','Study','Battle','Mine'],default='All',key='course_list_filter',label_visibility='collapsed')
    if filter_choice=='Mine':
        deck_rows=[('battle',deck) for deck in battle_decks if deck.get('owned')]+[('study',deck) for deck in study_decks if deck.get('owned')]
    else:
        deck_rows=[]
        if filter_choice in ('All','Battle'):deck_rows += [('battle',deck) for deck in battle_decks]
        if filter_choice in ('All','Study'):deck_rows += [('study',deck) for deck in study_decks]
    if not deck_rows:
        st.info('No matching decks yet. Create the first one above.')
        return
    for row in range(0,len(deck_rows),2):
        for column,(kind,deck) in zip(st.columns(2),deck_rows[row:row+2]):
            with column:
                with st.container(border=True,key=f'course_deck_{kind}_{deck["id"]}'):
                    icon=':material/menu_book:' if kind=='study' else ':material/swords:'
                    label='Study deck' if kind=='study' else 'Battle deck'
                    st.caption(icon+' '+label)
                    st.markdown('#### '+deck['name'])
                    st.caption(course_deck_meta(kind,deck))
                    if kind=='battle':key='course_battle_deck_'+deck['id']
                    else:key=('course_open_study_' if deck.get('owned') else 'course_copy_study_')+deck['id']
                    course_deck_action(client,kind,deck,key)


def course_deck_meta(kind,deck):
    if kind=='study':return f"{deck['course']} · {deck['language']} · By {deck['author']} · {deck['count']} questions"
    return f"{deck['course']} · {deck['language']} · By {deck.get('author','Student')} · {deck.get('count',15)} questions"


def course_deck_action(client,kind,deck,key,compact=False):
    """Open an owned Study deck, copy someone else's Study deck, or open a Battle deck."""
    if kind=='battle':
        # Battle Decks are played, not edited: start a Battle in the deck's course and language.
        if st.button('Start Battle',key=key,icon=':material/swords:',use_container_width=True):
            st.session_state.main_page='Play';st.session_state.play_mode_preview='Battle';st.session_state.battle_new_setup=True
            st.session_state.battle_course=deck['course'];st.session_state.battle_language=deck['language'];st.rerun()
    elif deck.get('owned'):
        if st.button('Open' if compact else 'Open Study deck',key=key,use_container_width=True):
            st.session_state.study_library=True;st.session_state.study_deck_open={'id':deck['id'],'shared':False};st.rerun()
    elif st.button('Save copy' if compact else 'Save private Study copy',key=key,use_container_width=True):
        if study_public_request(client,'copy',{'id':deck['id']}) is not None:
            st.success('Saved a private Study copy.');st.rerun()


def anki_import_screen(client,profile):
    from anki_import import AnkiImportError,parse_basic_apkg
    from db import AnkiImportRepository
    st.caption('Decks › Import from Anki')
    st.header('Import Basic Anki cards')
    st.info('Only two-field Basic text cards are accepted. Cloze, image and media cards stay in your Anki file and are not imported.')
    if st.button('Back to Decks'):
        st.session_state.pop('anki_import_open',None);st.session_state.pop('anki_import_result',None);st.session_state.pop('anki_import_saved',None);st.rerun()
    if saved:=st.session_state.get('anki_import_saved'):
        st.success(f"Saved {saved['count']} private source cards.")
        if st.button('Continue to question generation',type='primary'):
            st.session_state.pop('anki_import_open',None);st.session_state.pop('anki_import_saved',None);st.session_state.anki_generation_open=True;st.rerun()
        return
    upload=st.file_uploader('Anki package (.apkg)',type=['apkg'])
    if upload and st.button('Check Anki package',type='primary'):
        try:st.session_state.anki_import_result=parse_basic_apkg(upload.getvalue())
        except AnkiImportError as exc:st.error(str(exc));st.session_state.pop('anki_import_result',None)
    result=st.session_state.get('anki_import_result')
    if not result:return
    cards=result['cards'];skipped=result['skipped']
    reasons={'cloze':'Cloze cards are not supported yet.','image':'Image or media cards are not supported yet.','incomplete':'Cards without text on both sides were skipped.','unsupported':'Only two-field Basic cards are supported.','limit':'Only the first 100 valid Basic cards can be imported.'}
    st.success(f'{len(cards)} Basic text cards are ready to import.')
    for reason,text in reasons.items():
        count=sum(item['reason']==reason for item in skipped)
        if count:st.warning(f'{count}: {text}')
    if not cards:
        st.error('No importable Basic text cards were found.');return
    name=st.text_input('Import name',placeholder='For example: Corporate Finance Anki notes')
    course=st.selectbox('Course',profile['courses'],key='anki_import_course')
    language=st.selectbox('Deck language',profile['languages'],key='anki_import_language')
    if st.button(f'Save {len(cards)} source cards',type='primary'):
        try: saved=AnkiImportRepository(client).save(name=name,course=course,language=language,cards=cards)
        except ValueError as exc:st.error(str(exc))
        else:
            st.session_state.pop('anki_import_result',None)
            st.session_state.anki_import_saved=saved;st.rerun()

def pdf_import_screen(client,profile):
    from pdf_import import SlideImportError,parse_pdf_slides
    from db import AnkiImportRepository
    st.caption('Decks › AI from lecture slides')
    st.header('Import PDF lecture slides')
    st.info('PDF slides stay private. Only selectable text is supported; scanned PDFs need OCR before import.')
    if st.button('Back to Decks'):
        st.session_state.pop('pdf_import_open',None);st.session_state.pop('pdf_import_result',None);st.session_state.pop('pdf_import_saved',None);st.rerun()
    if saved:=st.session_state.get('pdf_import_saved'):
        st.success(f"Saved {saved['count']} private PDF sources.")
        if st.button('Continue to question generation',type='primary'):
            st.session_state.pop('pdf_import_open',None);st.session_state.pop('pdf_import_saved',None);st.session_state.anki_generation_open=True;st.rerun()
        return
    upload=st.file_uploader('Lecture slides (.pdf)',type=['pdf'])
    if upload and st.button('Check PDF slides',type='primary'):
        try:st.session_state.pdf_import_result=parse_pdf_slides(upload.getvalue())
        except SlideImportError as exc:st.error(str(exc));st.session_state.pop('pdf_import_result',None)
    result=st.session_state.get('pdf_import_result')
    if not result:return
    st.success(f"{len(result['cards'])} private text sources are ready to import.")
    if result['skipped']:st.warning(f"{result['skipped']} pages without selectable text were skipped.")
    if result['limited']:st.warning('Only the first 100 text sources were kept.')
    name=st.text_input('Import name',placeholder='For example: Corporate Finance lecture slides',key='pdf_import_name')
    course=st.selectbox('Course',profile['courses'],key='pdf_import_course')
    language=st.selectbox('Deck language',profile['languages'],key='pdf_import_language')
    if st.button(f"Save {len(result['cards'])} PDF sources",type='primary'):
        try:saved=AnkiImportRepository(client).save_slides(name=name,course=course,language=language,cards=result['cards'])
        except ValueError as exc:st.error(str(exc))
        else:
            st.session_state.pop('pdf_import_result',None);st.session_state.pdf_import_saved=saved;st.rerun()

def request_ai_generation(import_id,card_ids):
    if not st.session_state.get('ai_generation_request'):
        st.session_state.ai_generation_request={'import_id':import_id,'card_ids':list(card_ids)}


def generate_with_progress(repository,pending):
    """Run the single Edge Function call in the background and show an estimated progress bar."""
    import time
    from concurrent.futures import ThreadPoolExecutor
    from logic import ai_generation_estimate_seconds,ai_generation_progress
    count=len(pending['card_ids']);estimate=ai_generation_estimate_seconds(count)
    bar=st.progress(0.0,text=f'Generating {count} question drafts. Keep this page open.')
    started=time.monotonic()
    with ThreadPoolExecutor(max_workers=1) as pool:
        job=pool.submit(repository.generate,pending['import_id'],pending['card_ids'])
        while not job.done():
            fraction,left=ai_generation_progress(time.monotonic()-started,estimate)
            bar.progress(fraction,text=f'Generating {count} question drafts · {left}')
            time.sleep(.5)
    bar.empty()
    return job.result()


def anki_generation_screen(client,profile):
    """Select private source cards, generate drafts, then hand reviewed cards to Study."""
    from uuid import uuid4
    from db import AnkiImportRepository
    repository=AnkiImportRepository(client)
    st.caption('Decks › private sources › AI question generation')
    st.header('Generate reviewed questions')
    st.info('Select up to 100 private source cards. AI drafts stay private until you review and publish them as a Study deck.')
    if st.button('Back to Decks'):
        st.session_state.pop('anki_generation_open',None);st.rerun()
    try:imports=repository.imports()
    except ValueError as exc:st.error(str(exc));return
    if not imports:
        st.info('Import Anki cards or PDF lecture slides first. Your private sources will appear here after saving.');return
    choices={f"{item['name']} · {len(item['cards'])} source cards":item for item in imports}
    imported=choices[st.selectbox('Source import',list(choices))]
    st.caption(f"{imported['course']} · {imported['language']}")
    available=[card for card in imported['cards'] if not any(draft['source_card_id']==card['id'] and draft['status'] in ('draft','published') for draft in imported['drafts'])]
    if available:
        selected=[];st.subheader('1. Select source cards')
        select_all,clear=st.columns(2)
        if select_all.button('Select all available cards',use_container_width=True):
            for card in available:st.session_state['anki_source_'+card['id']]=True
            st.rerun()
        if clear.button('Clear selection',use_container_width=True):
            for card in available:st.session_state['anki_source_'+card['id']]=False
            st.rerun()
        for card in available:
            if st.checkbox(card['front'],help=card['back'],key='anki_source_'+card['id']):selected.append(card['id'])
        if pending:=st.session_state.pop('ai_generation_request',None):
            # The request leaves the session before the slow call, so a rerun can never
            # send it twice, and the button is not shown again until the call has ended.
            try:result=generate_with_progress(repository,pending)
            except ValueError as exc:result=None;st.error(str(exc))
            if result:st.session_state.notice=f"Generated {result['count']} private drafts. Review them below.";st.rerun()
        st.button(f'Generate {len(selected)} question drafts',type='primary',disabled=not selected,on_click=request_ai_generation,args=(imported['id'],selected))
    else:st.caption('All source cards from this import already have a draft or were published.')
    drafts=[draft for draft in imported['drafts'] if draft['status']=='draft']
    if not drafts:return
    st.subheader('2. Review drafts');selected_drafts=[]
    if st.button('Include all in Study Deck',key='ai_include_all_'+imported['id']):
        for draft in drafts:st.session_state['ai_include_'+draft['id']]=True
        st.rerun()
    for number,draft in enumerate(drafts,1):
        include,review=st.columns([.26,.74],vertical_alignment='center')
        if include.checkbox('Include in Study deck',key='ai_include_'+draft['id']):selected_drafts.append(draft)
        with review.expander(f"Draft {number}: {draft['question'][:70]}",expanded=number==1):
            question=st.text_area('Question',value=draft['question'],key='ai_question_'+draft['id'])
            options=[st.text_input(f'Answer {index+1}',value=option,key=f'ai_option_{draft["id"]}_{index}') for index,option in enumerate(draft['options'])]
            correct=st.radio('Correct answer',range(4),index=draft['correct_option_index'],format_func=lambda value:f'Answer {value+1}',horizontal=True,key='ai_correct_'+draft['id'])
            edit,discard=st.columns(2)
            if edit.button('Save edits',key='ai_save_'+draft['id']):
                try:repository.update_draft(draft['id'],question,options,correct)
                except ValueError as exc:st.error(str(exc))
                else:st.success('Draft saved.');st.rerun()
            if discard.button('Discard draft',key='ai_discard_'+draft['id']):
                try:repository.discard_draft(draft['id'])
                except ValueError as exc:st.error(str(exc))
                else:st.rerun()
    st.subheader('3. Publish after Study review')
    name=st.text_input('Study deck name',value=f"{imported['name']} questions",key='ai_study_name_'+imported['id'])
    if st.button(f'Create editable Study deck from {len(selected_drafts)} drafts',type='primary',disabled=not selected_drafts):
        cards=[]
        for draft in selected_drafts:
            answer_ids=[str(uuid4()) for _ in draft['options']]
            cards.append({'id':str(uuid4()),'question':draft['question'],'answers':[{'id':answer_id,'text':option} for answer_id,option in zip(answer_ids,draft['options'])],'correct_answer_id':answer_ids[draft['correct_option_index']],'allow_calculator':False,'chapter':''})
        st.session_state.study_draft={'id':str(uuid4()),'name':name,'course':imported['course'],'language':imported['language'],'cards':cards}
        st.session_state.study_revision=0;st.session_state.ai_draft_ids=[draft['id'] for draft in selected_drafts]
        st.session_state.pop('anki_generation_open',None);st.session_state.study_library=True;st.rerun()


def play_request(repository,action,data=None):
    try:return repository.action(action,data)
    except ValueError as exc:st.error(str(exc));return None


def navigate(page):
    if st.session_state.get('play_in_round'):
        st.session_state.play_exit_to=page
    else:
        if page=='Decks':
            for key in ('study_library','study_deck_open','deck_open','battle_deck_creator','battle_source_id','battle_return_study','anki_import_open','pdf_import_open','anki_generation_open'):
                st.session_state.pop(key,None)
        st.session_state.main_page=page
        if page=='Play':
            st.session_state.pop('study_active',None)
            st.session_state.pop('study_choose',None)
            st.session_state.pop('play_mode_preview',None)
            st.session_state.pop('battle_new_setup',None)
    st.rerun()


@st.fragment(run_every='1s')
def play_round_screen(client,duel_id):
    from db import PlayRepository
    repository=PlayRepository(client)
    session_partner_chat(client,'battle',duel_id)
    feedback=st.session_state.get('play_feedback')
    if feedback and feedback.get('duel_id')==duel_id:
        card=feedback['card'];response=feedback['feedback']
        st.subheader(f"Question {response['index']+1} of 30")
        st.write(card['question'])
        if response['timed_out']:st.warning('Time expired.')
        elif response['correct']:st.success('Correct!')
        else:st.error('That answer was incorrect.')
        for a in card['answers']:
            if a['id']==card['correct_answer_id']:st.success(a['text'])
            elif a['id']==response['answer_id']:st.error('Your answer: '+a['text'])
            else:st.write(a['text'])
        if st.button('Continue',type='primary'):
            st.session_state.pop('play_feedback',None);st.rerun()
        return
    result=play_request(repository,'round',{'duel_id':duel_id})
    if result is None:return
    state=result['state']
    if state in ('completed','pending'):
        st.session_state.play_in_round=False
        st.info('Your duel is complete.' if state=='completed' else 'Your round is saved. Waiting for your opponent.')
        if st.button('Back to Play'):
            st.session_state.pop('play_duel',None);st.rerun()
        return
    st.session_state.play_in_round=True
    if state=='feedback':
        st.session_state.play_feedback={**result,'duel_id':duel_id};st.rerun()
    if state=='rating':
        st.subheader('Your round is finished')
        st.metric('Correct answers',f"{result['score']} / 30")
        st.write('Rate each deck to save your completed round. Your individual ratings are private.')
        ratings={}
        for deck in result['decks']:
            ratings[deck['id']]=st.radio(deck['name'],['up','neutral','down'],index=None,format_func=lambda v:{'up':'Helpful','neutral':'Neutral','down':'Needs work'}[v],horizontal=True,key='rating_'+duel_id+deck['id'])
        if st.button('Finish round',type='primary',disabled=not all(ratings.values())):
            if play_request(repository,'finish',{'duel_id':duel_id,'ratings':ratings}) is not None:
                st.session_state.play_in_round=False;st.session_state.pop('play_duel',None);st.rerun()
        return
    st.progress(result['index']/30,text=f"Question {result['index']+1} of 30")
    st.caption(f":material/timer: {result['seconds']} seconds remaining · Closing this page does not reset the timer.")
    st.subheader(result['question'])
    question_tools(f'play_{duel_id}_{result["index"]}',result.get('allow_calculator') is True)
    cols=st.columns(2)
    for i,option in enumerate(result['options']):
        if cols[i%2].button(option['text'],key=f"play_answer_{duel_id}_{result['index']}_{option['id']}",use_container_width=True):
            response=play_request(repository,'answer',{'duel_id':duel_id,'index':result['index'],'answer_id':option['id']})
            if response is not None:
                clear_notepads()
                if response.get('state')=='feedback':st.session_state.play_feedback={**response,'duel_id':duel_id}
                st.rerun()


@st.fragment(run_every='10s')
def play_lobby(client,profile):
    from db import PlayRepository,DeckRepository
    repository=PlayRepository(client)
    state=play_request(repository,'list')
    if state is None:return
    if st.session_state.get('play_notice'):st.success(st.session_state.pop('play_notice'))
    st.caption('Asynchronous duels · 30 questions · 30 seconds per question · Finish within 24 hours of matching')
    with st.expander('Invitation settings'):
        paused=st.checkbox('Pause incoming duel invitations',value=state['paused'])
        if paused!=state['paused']:
            if play_request(repository,'set_pause',{'paused':paused}) is not None:st.rerun()
    if state['queue']:
        q=state['queue']
        st.info(f"Searching: {q['course']} · {q['language']} · {q['deck_name']}")
        st.caption('Expires '+q['expires_at']+' · You can leave and return. Refreshing does not extend the one-hour search.')
        if st.button('Cancel search'):
            if play_request(repository,'cancel_search') is not None:st.rerun()
    st.subheader('New duel')
    course=st.selectbox('Choose course',profile['courses'],key='play_course')
    try:all_decks=DeckRepository(client).list(course)
    except ValueError as exc:st.error(str(exc));return
    decks=[d for d in all_decks if d.get('language') in profile['languages']]
    if any(not d.get('language') for d in all_decks):st.caption('Some older decks need their creator to set a language in Decks before they can be played.')
    if not decks:st.info('No compatible decks yet. Create a deck in one of your profile languages, or ask its creator to set the deck language.')
    else:
        deck_id=st.selectbox('Your deck',[d['id'] for d in decks],format_func=lambda id:next(d['name']+' · '+d['language'] for d in decks if d['id']==id),key='play_deck')
        st.caption('Your 15 questions + your opponent’s 15 questions. Both players answer the same 30 questions. If you both choose the same deck, its questions appear twice.')
        mode=st.radio('Opponent',['Friend','Random player'],horizontal=True)
        if mode=='Random player':
            st.write('Match with a student from your university, in this course and deck language, who also starts a search. Searches last one hour.')
            if st.button('Find random player',type='primary',disabled=bool(state['queue'])):
                result=play_request(repository,'join',{'deck_id':deck_id})
                if result is not None:st.session_state.play_notice=result['message'];st.rerun()
        else:
            options=play_request(repository,'friend_options',{'deck_id':deck_id})
            if options is not None:
                friends=options['friends']
                if not friends:st.info('Add a friend first in Friends.')
                else:
                    friend_id=st.selectbox('Invite a friend',[f['id'] for f in friends],format_func=lambda id:next(f['username'] for f in friends if f['id']==id))
                    friend=next(f for f in friends if f['id']==friend_id)
                    confirmed=False
                    if not friend['speaks_language']:st.warning('This friend does not list the deck language in their profile.')
                    if not friend['has_course']:
                        st.warning('This friend has not added this course to their profile.')
                        confirmed=st.checkbox('Invite anyway',key='confirm_course_'+friend_id+'_'+deck_id)
                    if st.button('Send duel invitation',type='primary',disabled=not friend['speaks_language'] or (not friend['has_course'] and not confirmed)):
                        result=play_request(repository,'invite',{'deck_id':deck_id,'friend_id':friend_id,'confirm_missing_course':confirmed})
                        if result is not None:st.session_state.play_notice=result['message'];st.rerun()
    st.subheader('Invitations')
    if not state['invites']:st.caption('No pending invitations.')
    for inv in state['invites']:
        with st.container(border=True):
            st.write(('From ' if inv['incoming'] else 'To ')+inv['username'])
            st.caption(f"{inv['course']} · {inv['language']} · {inv['deck_name']} · Expires {inv['expires_at']}")
            if inv['incoming']:
                options=play_request(repository,'invite_decks',{'invite_id':inv['id']})
                if options and options['decks']:
                    chosen=st.selectbox('Choose your deck',[d['id'] for d in options['decks']],format_func=lambda id:next(d['name'] for d in options['decks'] if d['id']==id),key='accept_deck_'+inv['id'])
                    if chosen==inv['deck_id']:st.info('You selected the same deck: each of its 15 questions will appear twice.')
                    if st.button('Accept invitation',key='accept_duel_'+inv['id'],type='primary'):
                        result=play_request(repository,'accept',{'invite_id':inv['id'],'deck_id':chosen})
                        if result is not None:st.session_state.play_notice='Duel ready. Both players have 24 hours to finish.';st.rerun()
                if st.button('Decline',key='decline_duel_'+inv['id']):
                    if play_request(repository,'decline',{'invite_id':inv['id']}) is not None:st.rerun()
            elif st.button('Cancel invitation',key='cancel_duel_'+inv['id']):
                if play_request(repository,'cancel',{'invite_id':inv['id']}) is not None:st.rerun()
    for category in ['Ongoing','Pending','Completed']:
        st.subheader(category)
        duels=[d for d in state['duels'] if d['status']==category]
        if not duels:st.caption('No '+category.lower()+' duels.')
        for duel in duels:
            with st.container(border=True):
                st.write(f"**vs {duel['username']}** · {duel['course']} · {duel['language']}")
                st.caption('Deadline '+duel['deadline'])
                if category=='Ongoing':
                    if st.button('Resume round' if duel['started'] else 'Start round',key='start_'+duel['id'],type='primary'):
                        st.session_state.play_duel=duel['id'];st.session_state.pop('play_feedback',None);st.rerun()
                elif category=='Pending':st.info(f"Your score: {duel['score']}/30. Waiting for your opponent.")
                else:
                    st.write(f"{duel['result'].title()} · {duel['xp_delta']:+d} XP · Your score: {duel['score']}/30")
                    st.caption('Opponent: '+(str(duel['opponent_score'])+'/30' if duel['opponent_score'] is not None else 'Did not finish'))
                    if st.button('Review answers',key='review_'+duel['id']):
                        st.session_state.play_review=duel['id'];st.rerun()


def study_request(client,action,data=None):
    from db import StudyRepository
    return play_request(StudyRepository(client),action,data)


def study_public_request(client,action,data=None):
    from db import StudyRepository
    try:return StudyRepository(client).publication(action,data)
    except ValueError as exc:st.error(str(exc));return None


STUDY_LEVEL_COLORS={'new':'#CBD5E1','0':'#FECACA','1':'#FDBA74','2':'#FDE047','3':'#86EFAC'}
STUDY_LEVELS={'new':'New','0':'Needs practice','1':'Building confidence','2':'Getting stronger','3':'Well practised'}
STUDY_LEVEL_TITLES={'new':'New','0':'Needs practice','1':'Level 1 · Building confidence','2':'Level 2 · Getting stronger','3':'Level 3 · Well practised'}
STUDY_LEVEL_MEANINGS={'new':'Not answered yet.','0':'Answered, but no correct answer is counted at the moment.','1':'Answered correctly once.','2':'Answered correctly twice.','3':'Answered correctly three times, the highest level.'}


def study_level_selector(label,key):
    selected=[]
    with st.popover(label,icon=':material/filter_alt:',use_container_width=True):
        st.caption('Select one or more learning levels.')
        for level,name in STUDY_LEVEL_TITLES.items():
            swatch,option=st.columns([1,10],vertical_alignment='center')
            with swatch:st.html(f'<span aria-hidden="true" style="display:block;width:16px;height:16px;border-radius:5px;background:{STUDY_LEVEL_COLORS[level]}"></span>')
            if option.checkbox(name,value=True,key=key+'_'+level,help=STUDY_LEVEL_MEANINGS[level]):selected.append(level)
        st.caption('Each correct answer moves a question up one level; each wrong answer moves it down one.')
    chips=''.join(f'<span style="display:inline-flex;align-items:center;gap:7px;border:1px solid #80808055;border-radius:8px;padding:5px 8px"><span aria-hidden="true" style="width:12px;height:12px;border-radius:4px;background:{STUDY_LEVEL_COLORS[level]}"></span>{escape(STUDY_LEVEL_TITLES[level])}</span>' for level in selected)
    if selected:st.html('<div style="display:flex;flex-wrap:wrap;gap:6px;font-size:14px;margin-bottom:10px">'+chips+'</div>')
    else:st.caption('No learning levels selected.')
    return selected


def study_progress_summary(cards):
    counts={k:0 for k in STUDY_LEVELS}
    for c in cards:counts['new' if c.get('level') is None else str(c['level'])]+=1
    colors={'new':'#CBD5E1','0':'#FECACA','1':'#FDBA74','2':'#FDE047','3':'#86EFAC'}
    st.html('<style>'+ (Path(__file__).parent/'assets'/'study-design.css').read_text()+'</style><div class="study-legend">'+''.join(f'<div class="study-level"><span class="study-swatch" style="background:{colors[k]}"></span><span><strong>{STUDY_LEVEL_TITLES[k]}</strong><small>{STUDY_LEVEL_MEANINGS[k]}</small></span><b>{v}</b></div>' for k,v in counts.items())+'</div>')
    with st.popover(' ',icon=':material/info:',help='Learning progress legend'):
        explanations=[
            ('new','New','You have not answered this question yet.'),
            ('0','Needs practice','You answered incorrectly and have no earned steps remaining. One correct answer moves you to level 1.'),
            ('1','Level 1 · Building confidence','You have earned one step. Answer correctly to reach level 2; an incorrect answer returns you to red.'),
            ('2','Level 2 · Getting stronger','You have earned two steps. Answer correctly to reach level 3; an incorrect answer moves you back to level 1.'),
            ('3','Level 3 · Well practised','You have earned three steps—the highest level. Correct answers keep you here; an incorrect answer moves you back to level 2.')]
        st.write('**How your learning progress works**')
        for level,title,explanation in explanations:
            st.html(f'<div style="display:flex;gap:10px;align-items:flex-start;margin:8px 0;color:inherit"><span style="flex:0 0 16px;height:16px;margin-top:3px;border-radius:5px;background:{colors[level]}"></span><div><strong>{title}</strong><div style="font-size:14px;line-height:1.5;margin-top:3px">{explanation}</div></div></div>')
        st.caption('Each correct answer earns one step; each incorrect answer removes one. These levels describe your current progress, not your lifetime number of correct answers. Your first incorrect answer turns a new question red. Your progress stays private.')
    st.progress(sum((c.get('level') or 0) for c in cards)/(3*len(cards)) if cards else 0,text='Your learning progress')


def study_edit_change(field,key,index=None,answer=None):
    draft=st.session_state.study_draft
    st.session_state.pop('study_review',None)
    if index is None:draft[field]=st.session_state[key]
    elif answer is None:draft['cards'][index][field]=(st.session_state[key] or '') if field=='chapter' else st.session_state[key]
    else:draft['cards'][index]['answers'][answer]['text']=st.session_state[key]


def study_editor(client,profile):
    from logic import new_card,validate_card,validate_study_deck
    d=st.session_state.study_draft;revision=st.session_state.get('study_revision',0)
    st.subheader('Edit Study deck')
    st.caption('Add up to 100 questions. Your deck stays private until a together session shares a fixed copy with a partner who finishes.')
    if st.session_state.get('study_review'):
        st.warning('Review every question and correct answer before saving. Edits affect future sessions; received copies stay unchanged.')
        show_deck_cards(d['cards'])
        back,save=st.columns(2)
        if back.button('Back to Study editing'):st.session_state.pop('study_review');st.rerun()
        if save.button('Confirm and save Study deck',type='primary'):
            r=study_request(client,'save_deck',{'draft':validate_study_deck(d),'revision':revision,'review_id':st.session_state.study_review['id']})
            if r is not None:
                draft_ids=st.session_state.pop('ai_draft_ids',[])
                if draft_ids:
                    from db import AnkiImportRepository
                    try:AnkiImportRepository(client).publish_drafts(draft_ids)
                    except ValueError as exc:st.warning(str(exc))
                st.session_state.pop('study_draft');st.session_state.pop('study_review');st.session_state.study_deck_open={'id':r['id']};st.rerun()
        return
    for label,field,options in [('Course','course',profile['courses']),('Deck language','language',profile['languages'])]:
        key='study_edit_'+d['id']+field
        st.selectbox(label,options,index=options.index(d[field]) if d[field] in options else 0,key=key,on_change=study_edit_change,args=(field,key))
    key='study_edit_'+d['id']+'name'
    st.text_input('Study deck name',value=d['name'],key=key,on_change=study_edit_change,args=('name',key))
    index=st.selectbox('Question to edit',range(len(d['cards'])),format_func=lambda i:f"{i+1}. {d['cards'][i]['question'][:60] or 'New question'}",index=len(d['cards'])-1,key='study_edit_index_'+d['id']+'_'+str(len(d['cards'])))
    c=d['cards'][index];prefix='study_edit_'+c['id']
    st.subheader('Organise your questions')
    st.caption('Subsections group questions by topic or lecture. You can focus on these sections when studying alone. Choose an existing section or type a new one; leave it empty for General. Use a topic name that does not reveal the answer.')
    chapters=sorted({card.get('chapter','').strip() for card in d['cards'] if card.get('chapter','').strip()})
    current=c.get('chapter','').strip();key=prefix+'chapter'
    st.selectbox('Subsection / lecture',chapters,index=chapters.index(current) if current in chapters else None,accept_new_options=True,placeholder='Choose or type a subsection',key=key,on_change=study_edit_change,args=('chapter',key,index))
    if chapters:
        st.caption(' · '.join(f"{chapter}: {sum(card.get('chapter','').strip()==chapter for card in d['cards'])} questions" for chapter in chapters))
    key=prefix+'question'
    st.text_input('Question',value=c.get('question',''),key=key,on_change=study_edit_change,args=('question',key,index))
    for i,a in enumerate(c['answers']):
        key=prefix+a['id'];st.text_input(f'Answer {i+1}',value=a['text'],key=key,on_change=study_edit_change,args=('answers',key,index,i))
    ids=[a['id'] for a in c['answers']];key=prefix+'correct'
    st.radio('Correct answer',ids,index=ids.index(c['correct_answer_id']) if c['correct_answer_id'] in ids else None,format_func=lambda x:f'Answer {ids.index(x)+1}',key=key,on_change=study_edit_change,args=('correct_answer_id',key,index))
    key=prefix+'calculator'
    st.checkbox('Allow calculator for this question',value=c.get('allow_calculator',False),key=key,on_change=study_edit_change,args=('allow_calculator',key,index))
    add,delete=st.columns(2)
    if add.button('Add Study question',disabled=len(d['cards'])>=100):
        try:validate_card(c)
        except ValueError as exc:st.error(str(exc))
        else:
            added=new_card();added['chapter']=c.get('chapter','');d['cards'].append(added);st.rerun()
    if delete.button('Remove Study question',disabled=len(d['cards'])<=1):
        d['cards'].pop(index);st.rerun()
    st.caption(f"{len(d['cards'])} of 100 questions. Changing question content resets its learning level; changing a chapter label does not.")
    if st.button('Review Study deck',type='primary'):
        try:clean=validate_study_deck(d)
        except ValueError as exc:st.error(str(exc))
        else:
            r=study_request(client,'review_deck',{'draft':clean,'revision':revision})
            if r is not None:st.session_state.study_review=r;st.rerun()
    with st.expander('Discard unsaved Study changes'):
        if st.button('Confirm discard Study changes'):
            st.session_state.pop('study_draft');st.session_state.pop('study_review',None);st.rerun()


def study_library(client,profile):
    from uuid import uuid4
    from copy import deepcopy
    from logic import new_deck
    st.header('Study decks & progress')
    if st.session_state.get('study_draft'):
        study_editor(client,profile);return
    if st.session_state.get('study_deck_open'):
        choice=st.session_state.study_deck_open
        if st.button('Back to Study decks'):st.session_state.pop('study_deck_open');st.rerun()
        deck=study_request(client,'deck',choice)
        if deck is None:return
        st.subheader(deck['name']);st.caption(f"{deck['course']} · {deck.get('language')} · By {deck.get('author','you')} · {len(deck['cards'])} questions")
        study_progress_summary(deck['cards'])
        if choice.get('shared'):st.info('This is the permanent version shared in your study session. Later author changes are not included.')
        else:
            label='Create editable Study copy' if deck.get('legacy') else 'Edit Study deck'
            if st.button(label):
                d={k:deepcopy(deck[k]) for k in ['id','name','course','language','cards']}
                if deck.get('legacy'):d['id']=str(uuid4())
                st.session_state.study_draft=d;st.session_state.study_revision=0 if deck.get('legacy') else deck['revision'];st.session_state.pop('study_review',None);st.rerun()
            if not deck.get('legacy'):
                enough=len(deck['cards'])>=15
                if st.button('Publish as Battle deck',key='study_publish_battle',icon=':material/swords:',type='primary',use_container_width=True,disabled=not enough):
                    st.session_state.battle_deck_creator=True;st.session_state.battle_source_id=deck['id'];st.session_state.battle_return_study=True;st.rerun()
                st.caption('Pick 15 questions from this deck for a public Battle deck. This Study deck stays unchanged.' if enough else f"Battle decks need at least 15 questions. This deck has {len(deck['cards'])}.")
        for i,c in enumerate(deck['cards']):
            level='new' if c.get('level') is None else str(c['level'])
            with st.expander(f"{i+1}. {c.get('chapter') or 'General'} · {STUDY_LEVEL_TITLES[level]} · {c['question']}"):
                show_deck_cards([c])
                if c.get('note'):st.info('Your private note: '+c['note'])
                for f in c.get('feedback',[]):st.caption('Feedback you sent: '+f)
        return
    data=study_request(client,'list')
    if data is None:return
    public=study_public_request(client,'list')
    if public is None:return
    published_ids=set(public.get('published_ids',[]))
    if st.button('Create Study deck',type='primary'):
        st.session_state.study_draft=new_deck(profile['courses'][0],profile['languages'][0]);st.session_state.study_revision=0;st.rerun()
    st.caption('Study decks have flexible question counts and chapters. Existing published decks remain available below.')
    for title,key in [('Your decks','decks'),('Shared with me','shared')]:
        st.subheader(title)
        if not data[key]:st.caption('No decks yet.' if key=='decks' else 'Finish a together session to receive your partner’s full deck.')
        for d in data[key]:
            with st.container(border=True):
                st.write('**'+d['name']+'**');st.caption(f"{d['course']} · {d.get('language') or 'Set a language first'} · {d['count']} questions")
                if st.button('View progress and questions',key='study_open_'+d['id']):
                    st.session_state.study_deck_open={'id':d['id'],'shared':key=='shared'};st.rerun()
                if key=='decks':
                    if d['id'] in published_ids:
                        st.caption('Published to students at your university.')
                        if st.button('Unpublish Study deck',key='study_unpublish_'+d['id']):
                            if study_public_request(client,'unpublish',{'id':d['id']}) is not None:st.rerun()
                    elif st.button('Publish Study deck',key='study_publish_'+d['id'],type='primary'):
                        if study_public_request(client,'publish',{'id':d['id']}) is not None:st.rerun()
    st.subheader('Published Study decks')
    st.caption('Your published decks and decks published by compatible students at your university.')
    if not public.get('decks'):st.caption('No published Study decks match your profile yet.')
    for d in public.get('decks',[]):
        with st.container(border=True):
            st.write('**'+d['name']+'**');st.caption(f"{d['course']} · {d['language']} · By {d['author']} · {d['count']} questions")
            if d.get('owned'):
                st.caption('Your published Study deck.')
                if st.button('Open your Study deck',key='study_open_public_'+d['id']):
                    st.session_state.study_deck_open={'id':d['id'],'shared':False};st.rerun()
            elif st.button('Save private Study copy',key='study_copy_public_'+d['id']):
                copied=study_public_request(client,'copy',{'id':d['id']})
                if copied is not None:
                    st.success('Saved a private Study copy.');st.rerun()
    with st.expander('Feedback on your questions'):
        if not data['feedback']:st.caption('No feedback yet.')
        for f in data['feedback']:
            st.write(f['question']);st.info(f['body']);st.caption(f"From {f['username']} · {f['created_at']}")


def study_round_screen(client,sid):
    r=study_request(client,'round',{'id':sid})
    if r is None:return
    from db import StudyRepository
    try:progress=StudyRepository(client).progress(sid)
    except ValueError as exc:st.error(str(exc));return
    st.html('<style>'+ (Path(__file__).parent/'assets'/'study-round.css').read_text()+'</style>')
    session_partner_chat(client,'study',sid)
    if st.button('Save and leave Study session'):
        st.session_state.pop('study_session',None);st.rerun()
    state=r['state']
    if state in ('question','feedback'):
        from study_ui import study_progress_tiles
        symbols={'correct':'✓','incorrect':'×','current':'•','open':''}
        current_index=r['index'] if state=='question' else r['index']+1
        tiles=study_progress_tiles(progress.get('answers',[]),current_index,r['total'])
        markup=''.join(f'<span class="study-tile study-tile-{tile["state"]}" aria-label="Question {tile["number"]}: {tile["state"]}">{symbols[tile["state"]] or tile["number"]}</span>' for tile in tiles)
        question,overview=st.columns([3,1],gap='large')
        with overview:
            st.html('<aside class="study-overview"><h3>Overview</h3><div class="study-overview-grid">'+markup+'</div></aside>')
        with question:
            st.caption(f"Question {r['index']+1} of {r['total']}")
            if state=='question':
                st.caption(r['part']+' · '+(r.get('chapter') or 'General'))
                if r.get('deadline'):st.caption('Finish by '+r['deadline'])
                st.html('<div class="study-question-card">'+escape(r['question'])+'</div>')
                question_tools(f'study_{sid}_{r["index"]}',r.get('allow_calculator') is True)
                cols=st.columns(2)
                for i,a in enumerate(display_options(r['options'],sid,r['index'])):
                    if cols[i%2].button(a['text'],key=f"study_answer_{sid}_{r['index']}_{a['id']}",use_container_width=True):
                        if study_request(client,'answer',{'id':sid,'index':r['index'],'answer_id':a['id']}) is not None:
                            clear_notepads();st.rerun()
            else:
                c=r['card'];st.caption(c.get('chapter') or 'General');st.html('<div class="study-question-card">'+escape(c['question'])+'</div>')
                if r['correct']:st.success('Correct!')
                else:st.error('Not quite. Review the correct answer below.')
                answer_markup=''.join('<div class="study-answer-card '+('is-correct is-correct-animated' if a['id']==c['correct_answer_id'] and r['correct'] else 'is-correct' if a['id']==c['correct_answer_id'] else 'is-incorrect' if a['id']==r['answer_id'] else 'is-neutral')+'">'+escape(a['text'])+'</div>' for a in display_options(c['answers'],sid,r['index']))
                st.html('<div class="study-answer-grid">'+answer_markup+'</div>')
                prefix=f"{sid}_{r['index']}"
                with st.expander('Private note / feedback to author'):
                    note=st.text_area('Private note',value=c.get('note',''),max_chars=4000,key='study_note_'+prefix)
                    if st.button('Save private note',key='study_save_note_'+prefix):
                        if study_request(client,'annotate',{'id':sid,'index':r['index'],'note':note}) is not None:st.success('Private note saved.')
                    feedback=st.text_area('Feedback for the author',max_chars=2000,key='study_feedback_'+prefix)
                    st.caption('Sent feedback is visible to the author and kept with this question for you. Your private note is not sent.')
                    if st.button('Send feedback to author',key='study_send_'+prefix,disabled=not feedback.strip()):
                        if study_request(client,'annotate',{'id':sid,'index':r['index'],'feedback':feedback}) is not None:st.success('Feedback sent.')
                if st.button('Next question' if r['index']+1<r['total'] else 'See session result',type='primary'):
                    if study_request(client,'next',{'id':sid,'index':r['index']}) is not None:st.rerun()
        return
    elif state=='completed':
        st.subheader(r['result']);st.metric('Your correct answers',f"{r['score']} / {r['total']}")
        if r.get('opponent_score') is not None:st.metric('Partner’s correct answers',f"{r['opponent_score']} / {r['total']}")
        st.caption('Study Mode does not change XP, rankings or win streaks.')
        if r.get('shared'):st.success('Your partner’s full deck is available under Decks → Study decks & progress → Shared with me.')
        if st.button('Refresh session result'):st.rerun()
    elif state=='waiting':
        st.info('Your practice is saved. Waiting for a partner—there is no need to stay online.')
        st.caption('Search / invitation expires: '+str(r.get('expires_at')))
        if st.button('Check for a study partner'):st.rerun()
        if st.button('Cancel this search or invitation'):
            if study_request(client,'cancel',{'id':sid}) is not None:st.rerun()
    else:st.info('This session '+state+'. Your completed practice and notes are saved.')


WEEKDAYS=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']


def study_plan_request(client,action,data=None):
    from db import StudyPlanRepository
    return play_request(StudyPlanRepository(client),action,data)


def study_plan_quiet(client,action,data=None):
    """Study plan request for places where the plan is an extra: problems are not shown."""
    from db import StudyPlanRepository
    try:return StudyPlanRepository(client).action(action,data)
    except ValueError:return None


def study_plan_decks(client,data=None):
    """Decks the student can study, by course: their own and copies earned by studying with friends."""
    data=data or study_request(client,'list')
    if data is None:return None
    grouped={}
    for key,shared in (('decks',False),('shared',True)):
        for d in data.get(key,[]):grouped.setdefault(d['course'],[]).append({'id':d['id'],'name':d['name']+(' (shared with me)' if shared else ''),'shared':shared,'count':d.get('count',0)})
    return grouped


def study_plan_levels(client,plan,decks,by_deck=None):
    """Current learning level of every question in the plan, per course. The plan only reads progress."""
    lookup={d['id']:d for items in decks.values() for d in items};levels={};by_deck={} if by_deck is None else by_deck
    for item in plan['courses']:
        levels[item['course']]=[]
        for deck_id in item['decks']:
            if deck_id not in lookup:continue
            full=study_request(client,'deck',{'id':deck_id,'shared':lookup[deck_id]['shared']})
            if full is None:return None
            by_deck[deck_id]=[c.get('level') for c in full.get('cards',[])];levels[item['course']]+=by_deck[deck_id]
    return levels


def study_plan_start(client,plan,course,steps,by_deck,decks):
    """Start a solo Study session for one course of the plan, from the deck with the most questions below the target."""
    from uuid import uuid4
    lookup={d['id']:d for items in decks.values() for d in items};item=next(c for c in plan['courses'] if c['course']==course)
    waiting={d:sum(1 for level in by_deck.get(d,[]) if (level or 0)<plan['target']) for d in item['decks'] if d in lookup}
    deck_id=max(waiting,key=waiting.get,default=None)
    if not deck_id or not waiting[deck_id]:
        st.info('Every question of this course has reached your target level.');return
    started=study_request(client,'start',{'deck_id':deck_id,'shared':lookup[deck_id]['shared'],'mode':'solo','count':min(steps,waiting[deck_id],100),'chapters':[],'levels':['new']+[str(level) for level in range(plan['target'])],'request_id':str(uuid4())})
    if started is not None:
        st.session_state.study_active=True;st.session_state.study_choice='Study alone';st.session_state.study_session=started['id'];st.session_state.main_page='Play';st.rerun()


def study_plan_clock():
    """The student's current time of day, from the browser's time zone when it is known."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    try:return datetime.now(ZoneInfo(st.context.timezone)).time()
    except Exception:return datetime.now().time()


def study_plan_today(client,plan,levels,by_deck,decks,today,prefix):
    """Today's sessions of one plan with a start button for everything still open. The day's amount is fixed once per day."""
    import study_plan as rules
    now=study_plan_clock()
    if (plan.get('day') or {}).get('date')!=today.isoformat():
        plan['day']=rules.day_snapshot(plan,levels,today)
        if plan['day']['planned']:study_plan_quiet(client,'save',{'id':plan['id'],'plan':{k:v for k,v in plan.items() if k not in ('id','calendar_events')}})
    sessions=rules.today_sessions(plan,levels,today)
    if not sessions:
        st.caption('No session planned for today.');return
    st.write("**Today's sessions**")
    for index,session in enumerate(sessions):
        if not session['open']:
            st.caption(f":material/check_circle: {session['name']} session ({session['time']}) is done.");continue
        for course,steps in session['courses'].items():
            action='Catch up on' if rules.session_overdue(session['time'],now) else 'Start'
            if st.button(f"{action} {session['name'].lower()} session · {course} · {steps} questions",key=f"{prefix}_start_{plan['id']}_{index}_{course}",icon=':material/play_arrow:',use_container_width=True,help=f"Planned for {session['time']}. You can do it at any time today."):
                study_plan_start(client,plan,course,steps,by_deck,decks)


def study_plan_play_todos(client,study_data,prefix='todo'):
    """Open study plan sessions of today, listed with the ongoing Study sessions on Play."""
    from datetime import date
    data=study_plan_quiet(client,'list')
    if not data or not data.get('plans') or not study_data:return
    decks=study_plan_decks(client,study_data);today=date.today()
    st.markdown('**:material/event_available: Study plan to-dos**')
    for stored in data['plans']:
        plan={**stored['plan'],'id':stored['id']};by_deck={};levels=study_plan_levels(client,plan,decks,by_deck)
        if levels is None:continue
        with st.container(border=True):
            st.write('**'+plan['name']+'**');study_plan_today(client,plan,levels,by_deck,decks,today,prefix)


def study_plan_workload_text(rules,plan,item,levels,today,schedule):
    from datetime import date
    from math import ceil
    steps=rules.remaining_steps(levels,plan['target']);end=date.fromisoformat(item['end']);outlook=rules.course_outlook(schedule,item['course'])
    if not levels:return f"{item['course']}: the selected decks have no questions yet."
    if steps==0:return f"{item['course']}: every question has reached level {plan['target']}."
    if end<today:return f"{item['course']}: ended on {end:%d %b %Y} with {steps} answers still open."
    if not outlook:return f"{item['course']}: there is no study day left before {end:%d %b %Y}."
    per_session=f", {ceil(outlook['per_day']/plan['sessions'])} per session" if plan['sessions']>1 else ''
    starting=f" from {outlook['first']:%d %b}" if outlook['first']>today else ''
    early=(end-outlook['finish']).days
    hint=f"You will be done on {outlook['finish']:%d %b}, {early} day{'s' if early!=1 else ''} before your target date." if early>0 else f"You will be done on your target date, {outlook['finish']:%d %b}."
    return f"{item['course']}: **{outlook['per_day']} questions per day**{per_session}, on {outlook['days']} study day{'s' if outlook['days']!=1 else ''}{starting}. {hint}"


def study_plan_total_text(schedule):
    first=min(schedule) if schedule else None
    return f"All courses together: **{sum(schedule[first].values())} questions** on your next study day, {first:%d %b}." if first else ''


def study_plan_live_preview(rules,plan,levels,today,schedule):
    """Read-only summary for the editor; it deliberately reuses the real schedule."""
    from datetime import timedelta
    from math import ceil
    with st.container(border=True,key='study_plan_preview_editor'):
        st.subheader('Live preview')
        upcoming=next(iter(schedule),None)
        if upcoming:
            total=sum(schedule[upcoming].values())
            session=ceil(total/plan['sessions'])
            stats=st.columns(2)
            with stats[0]:st.html(f'<div class="study-plan-preview-stat">Per study day<strong>~{total} q</strong></div>')
            with stats[1]:st.html(f'<div class="study-plan-preview-stat">Per session<strong>~{session} q</strong></div>')
            maximum=max((sum(items.values()) for items in schedule.values()),default=1)
            exams={item['end'] for item in plan['courses']}
            cells=[]
            for offset in range(28):
                day=today+timedelta(days=offset);amount=sum(schedule.get(day,{}).values())
                state=' exam' if day.isoformat() in exams else (' load-'+str(min(3,max(1,ceil(amount/maximum*3)))) if amount else '')
                cells.append(f'<span class="{state.strip()}" title="{day:%d %b}: {amount} questions"></span>')
            st.caption('Next 4 weeks')
            st.html('<div class="study-plan-heatmap" aria-label="Next four weeks of the study plan">'+''.join(cells)+'</div>')
            st.caption('Darker = more questions · coral = exam')
            st.caption('The preview is recalculated from your current learning progress.')
        else:
            st.info('Choose valid courses, dates and decks to see the workload preview.')
            return
        for item in plan['courses']:
            outlook=rules.course_outlook(schedule,item['course'])
            if outlook:
                each=ceil(outlook['per_day']/plan['sessions'])
                st.write(f"**{item['course']}** · ~{each} questions per session")
        st.success(f"Your plan uses {plan['sessions']} session{'s' if plan['sessions'] != 1 else ''} on each study day.")


def study_plan_close_editor():
    for k in [k for k in st.session_state if str(k).startswith('plan_')]:st.session_state.pop(k,None)


def study_plan_design():
    st.html('<style>'+(Path(__file__).parent/'assets'/'study-plan.css').read_text()+'</style>')


def study_plan_add_day_off(key):
    extra=st.session_state.get(key+'extra_day')
    if extra:
        for part in ('dates_options','dates_off'):st.session_state[key+part]=sorted(set(st.session_state.get(key+part,[]))|{extra.isoformat()})


def study_plan_editor(client,profile,decks,user_id=''):
    from datetime import date,time,timedelta
    import study_plan as rules
    draft=st.session_state.plan_draft;today=date.today();key='plan_'+str(draft.get('id','new'))+'_'
    heading,actions=st.columns([3,1],vertical_alignment='center')
    with heading:
        label='Edit plan' if draft.get('id') else 'New plan'
        st.markdown(f'<p class="study-plan-breadcrumb">Study plan › <strong>{label}</strong></p>',unsafe_allow_html=True)
    configuration,preview=st.columns([1.28,.82],vertical_alignment='top')
    with configuration:
        with st.container(border=True,key='study_plan_editor_courses'):
            st.markdown('<p class="study-plan-step-heading"><span class="study-plan-step-number">1</span>Courses and exams</p>',unsafe_allow_html=True)
            name=st.text_input('Plan name',value=draft['name'],max_chars=60,key=key+'name',placeholder='Plan name, like Winter exams')
            courses=st.multiselect('Courses',profile['courses'],default=[c['course'] for c in draft['courses'] if c['course'] in profile['courses']],key=key+'courses',help='Only courses from your profile can be added.')
            chosen=[]
            for course in courses:
                old=next((c for c in draft['courses'] if c['course']==course),None);options=decks.get(course,[]);ids=[d['id'] for d in options]
                with st.container(border=True,key=key+'course_'+course):
                    st.write('**'+course+'**')
                    if not options:st.warning('You have no Study decks for this course yet.')
                    first,last=st.columns(2)
                    begin=first.date_input('Start studying on',value=max(date.fromisoformat(old['start']),today) if old and old.get('start') else today,min_value=today,key=key+'start_'+course,help='Today means you start right away. Pick a later day to begin closer to the exam.')
                    end=last.date_input('Finish by (exam or target date)',value=max(date.fromisoformat(old['end']),today) if old else today+timedelta(days=14),min_value=today,key=key+'end_'+course)
                    start=begin.isoformat() if begin>today else None
                    picked=st.multiselect('Decks to study',ids,default=[d for d in (old['decks'] if old else []) if d in ids],format_func=lambda i,options=options:next(f"{d['name']} · {d['count']} questions" for d in options if d['id']==i),key=key+'decks_'+course)
                    chosen.append({'course':course,'start':start,'end':end.isoformat(),'decks':picked})
        with st.container(border=True,key='study_plan_editor_goal'):
            goal_heading,legend=st.columns([5,1],vertical_alignment='bottom')
            with goal_heading:st.markdown('<p class="study-plan-step-heading"><span class="study-plan-step-number">2</span>Goal for every question</p>',unsafe_allow_html=True)
            target_key=key+'target_choice'
            if target_key not in st.session_state:st.session_state[target_key]=draft['target']
            target=st.session_state[target_key]
            goal_text={1:('Correct once','Level 1'),2:('Correct twice','Level 2'),3:('Correct three times','Level 3')}
            for target_col,value in zip(st.columns(3),(1,2,3)):
                selected=target==value
                with target_col:
                    with st.container(border=True,key=f'study_plan_goal_card_{value}'+('_selected' if selected else '')):
                        if st.button(goal_text[value][1],key=key+f'goal_{value}',use_container_width=True):
                            st.session_state[target_key]=value;st.rerun()
                        st.caption(goal_text[value][0])
                        if value==2:st.caption('Recommended')
            with legend.popover(' ',icon=':material/info:',help='What the learning levels mean'):
                st.write('**Learning levels**')
                for v,text in [(1,'One correct answer earned.'),(2,'Two correct answers earned.'),(3,'Three correct answers earned, the highest level.')]:
                    st.html(f'<div style="display:flex;gap:10px;align-items:flex-start;margin:8px 0;color:inherit"><span style="flex:0 0 16px;height:16px;margin-top:3px;border-radius:5px;background:{STUDY_LEVEL_COLORS[str(v)]}"></span><div><strong>Level {v} · {escape(STUDY_LEVELS[str(v)])}</strong><div>{text}</div></div></div>')
                st.caption('Each correct answer moves a question up one level and each wrong answer moves it down one. The plan counts how many levels every question still has to climb to your target.')
        with st.container(border=True,key='study_plan_editor_week'):
            st.markdown('<p class="study-plan-step-heading"><span class="study-plan-step-number">3</span>Your week</p>',unsafe_allow_html=True)
            st.markdown('**Study days**')
            study_days_key=key+'study_days'
            if study_days_key not in st.session_state:st.session_state[study_days_key]=[day for day in range(7) if day not in draft['weekdays_off']]
            study_days=set(st.session_state[study_days_key])
            for day_col,day in zip(st.columns(7),range(7)):
                with day_col:
                    if st.button(WEEKDAYS[day][:2],key=key+f'study_day_{day}',type='primary' if day in study_days else 'secondary',use_container_width=True):
                        updated=study_days^{day}
                        if updated:
                            st.session_state[study_days_key]=sorted(updated);st.rerun()
            weekdays_off=[day for day in range(7) if day not in study_days]
            st.caption('Optional: add single dates without studying, such as holidays.')
            for part in ('dates_options','dates_off'):
                if key+part not in st.session_state:st.session_state[key+part]=list(draft['dates_off'])
            pick,add=st.columns([3,1],vertical_alignment='bottom')
            pick.date_input('Single day without studying',value=None,min_value=today,key=key+'extra_day')
            add.button('Add day off',on_click=study_plan_add_day_off,args=(key,),key=key+'add_day')
            dates_off=st.multiselect('Days off',st.session_state[key+'dates_options'],key=key+'dates_off',help='Remove a date to study on it again.') if st.session_state[key+'dates_options'] else []
            st.markdown('**Sessions per study day**')
            sessions_key=key+'sessions_choice'
            if sessions_key not in st.session_state:st.session_state[sessions_key]=draft['sessions']
            sessions=st.session_state[sessions_key]
            for session_col,amount in zip(st.columns(3),(1,2,3)):
                with session_col:
                    if st.button(str(amount),key=key+f'session_{amount}',type='primary' if sessions==amount else 'secondary',use_container_width=True):
                        st.session_state[sessions_key]=amount;st.rerun()
            st.caption('A session is one sitting in Study Mode. Splitting a day into 2 or 3 sessions keeps each sitting short; every session gets its own start time and calendar entry.')
            times=[]
            for i,col in enumerate(st.columns(sessions)):
                suggested=draft['times'][i] if i<len(draft['times']) else rules.DEFAULT_TIMES[i]
                times.append(col.time_input(f'Session {i+1} starts at',value=time.fromisoformat(suggested),step=900,key=key+f'time_{i}').strftime('%H:%M'))
    plan={'name':name,'target':target,'sessions':sessions,'times':times,'weekdays_off':weekdays_off,'dates_off':dates_off,'courses':chosen};clean=None
    try:clean=rules.validate_plan(plan,profile['courses'],decks,today)
    except ValueError as exc:validation_error=str(exc)
    else:validation_error=''
    levels=None;schedule={}
    if clean:
        levels=study_plan_levels(client,clean,decks)
        if levels is not None:schedule=rules.plan_schedule(clean,levels,today)
    with preview:
        if validation_error:st.info(validation_error)
        elif levels is not None:
            study_plan_live_preview(rules,clean,levels,today,schedule)
            with st.container(border=True,key='study_plan_editor_workload'):
                st.write('**Your workload**')
                for item in clean['courses']:st.write(study_plan_workload_text(rules,clean,item,levels[item['course']],today,schedule))
                if len(clean['courses'])>1 and schedule:st.write(study_plan_total_text(schedule))
        else:st.info('Choose courses, decks and dates to see the live preview.')
    with actions:
        cancel_action,save_action=st.columns(2)
        cancel=cancel_action.button('Cancel',use_container_width=True)
        save=save_action.button('Save study plan',type='primary',disabled=clean is None,use_container_width=True)
    if save:
        payload={'plan':clean}
        if draft.get('id'):payload['id']=draft['id']
        saved=study_plan_request(client,'save',payload)
        if saved is not None:
            study_plan_close_editor();st.session_state.study_plan_finish=saved['id'];st.rerun()
    if cancel:
        study_plan_close_editor();st.rerun()
    if draft.get('id'):
        import google_calendar as google
        st.divider();st.write('**Calendar**')
        st.caption('These use the plan as it is saved now. Save your changes first to include them.')
        saved={k:v for k,v in draft.items() if k!='calendar_events'};recorded=draft.get('calendar_events') or [];saved_levels=study_plan_levels(client,saved,decks)
        if saved_levels is not None:study_plan_calendar_buttons(saved,recorded,saved_levels,today,user_id)
        st.divider()
        if not st.session_state.get(key+'delete'):
            if st.button('Delete study plan',icon=':material/delete:',key=key+'delete_ask'):
                st.session_state[key+'delete']=True;st.rerun()
        else:
            st.warning(f"Delete the study plan “{draft['name']}”? Your learning progress is kept.")
            client_id,secret,redirect=study_plan_google_settings()
            if recorded and client_id and secret:
                st.caption(f'{len(recorded)} entries of this plan are in your Google Calendar. Remove them first if you no longer want them.')
                st.link_button('Remove from Google Calendar',google.authorization_url(client_id,redirect,google.sign_state(secret,'clear',draft['id'],user_id)))
            yes,no=st.columns(2)
            if yes.button('Confirm deletion',type='primary',key=key+'delete_yes',use_container_width=True):
                if study_plan_request(client,'delete',{'id':draft['id']}) is not None:
                    study_plan_close_editor();st.rerun()
            if no.button('Keep plan',key=key+'delete_no',use_container_width=True):
                st.session_state.pop(key+'delete',None);st.rerun()


def study_plan_google_settings():
    return config('GOOGLE_CLIENT_ID'),config('GOOGLE_CLIENT_SECRET'),(config('APP_URL') or 'http://localhost:8501').rstrip('/')


def study_plan_google_answer(client,decks,user_id):
    """After Google sends the student back: update the plan's calendar entries once, with a short-lived token."""
    from datetime import date
    import httpx
    import google_calendar as google
    import study_plan as rules
    state=str(st.query_params.get('state',''))
    if not state.startswith(google.STATE_PREFIX):return
    code=st.query_params.get('code')
    for name in ('state','code','error','scope','authuser','prompt','hd','iss'):
        if name in st.query_params:del st.query_params[name]
    if not code:
        st.warning('Google Calendar was not changed because the permission was not granted.');return
    client_id,secret,redirect=study_plan_google_settings()
    try:
        request=google.read_state(secret,state,user_id)
        data=study_plan_request(client,'list')
        if data is None:return
        stored=next((p for p in data['plans'] if p['id']==request['plan_id']),None)
        if stored is None:raise ValueError('This study plan is no longer available. Google Calendar was not changed.')
        plan={**stored['plan'],'id':stored['id']};created=[];failed=0
        with httpx.Client(timeout=15) as http:
            token=google.exchange_code(http,client_id,secret,redirect,code)
            events=[]
            if request['kind']=='sync':
                levels=study_plan_levels(client,plan,decks)
                if levels is None:return
                try:timezone=st.context.timezone or 'UTC'
                except Exception:timezone='UTC'
                events=[{'uid':rules.session_uid(plan,s),'body':google.event_body(rules.session_title(plan,s),rules.session_details(s),s['date'],s['time'],rules.session_minutes(s['steps']),timezone)} for s in rules.plan_sessions(plan,levels,date.today())]
            left=google.remove_events(http,token,stored['calendar_events'])
            if events:created,failed=google.add_events(http,token,events)
        if study_plan_request(client,'events',{'id':stored['id'],'events':left+created}) is None:return
        if left or failed:st.warning(f"Google Calendar was only partly updated for {plan['name']}: {len(created)} entries added, {failed} could not be added and {len(left)} old entries could not be removed. Choose Update Google Calendar to try again.")
        elif request['kind']=='sync':st.success(f"Google Calendar now has {len(created)} entries for {plan['name']}.")
        else:st.success(f"The Google Calendar entries for {plan['name']} were removed.")
    except ValueError as exc:st.error(str(exc))
    except httpx.HTTPError:st.error('Google Calendar could not be reached. Choose Update Google Calendar to try again.')


def study_plan_calendar_buttons(plan,recorded,levels,today,user_id):
    """Calendar file download and Google Calendar link for one saved plan."""
    import google_calendar as google
    import study_plan as rules
    client_id,secret,redirect=study_plan_google_settings();download,online=st.columns(2)
    download.download_button('Calendar file',rules.plan_ics(plan,rules.plan_sessions(plan,levels,today)),file_name='uniarena-'+plan['id'][:8]+'.ics',mime='text/calendar',key='plan_ics_'+plan['id'],icon=':material/download:',use_container_width=True,help='Download the planned sessions and import them into any calendar.')
    if client_id and secret:
        online.link_button('Update Google Calendar' if recorded else 'Add to Google Calendar',google.authorization_url(client_id,redirect,google.sign_state(secret,'sync',plan['id'],user_id)),icon=':material/event:',use_container_width=True)
        st.caption((f'{len(recorded)} entries of this plan are in your Google Calendar. After changing the plan or missing a day, choose Update Google Calendar. ' if recorded else '')+'Google asks for permission each time; UniArena only changes the entries it created for this plan.')
    else:st.caption('Google Calendar is not connected to this app yet. Use the calendar file instead.')


def study_plan_finish(client,stored,decks,user_id):
    """Step after saving: put the sessions into a calendar if wanted, then finish to see the progress overview."""
    from datetime import date
    import study_plan as rules
    plan={**stored['plan'],'id':stored['id']};today=date.today()
    st.subheader('Study plan saved: '+plan['name'])
    levels=study_plan_levels(client,plan,decks)
    if levels is None:return
    schedule=rules.plan_schedule(plan,levels,today)
    for item in plan['courses']:st.write(study_plan_workload_text(rules,plan,item,levels[item['course']],today,schedule))
    if len(plan['courses'])>1 and schedule:st.write(study_plan_total_text(schedule))
    st.write('**Add the sessions to your calendar**')
    st.caption('Optional. Download a calendar file or add the sessions to Google Calendar, then finish to see your progress.')
    study_plan_calendar_buttons(plan,stored.get('calendar_events') or [],levels,today,user_id)
    if st.button('Finish',type='primary',use_container_width=True):
        st.session_state.pop('study_plan_finish',None);st.rerun()


def study_plan_screen(client,profile,user_id=''):
    from datetime import date
    import google_calendar as google
    import study_plan as rules
    study_plan_design()
    decks=study_plan_decks(client)
    if decks is None:return
    study_plan_google_answer(client,decks,user_id)
    if 'plan_draft' in st.session_state:return study_plan_editor(client,profile,decks,user_id)
    st.title('Study Plan')
    data=study_plan_request(client,'list')
    if data is None:return
    saved=next((p for p in data['plans'] if p['id']==st.session_state.get('study_plan_finish')),None)
    if saved:return study_plan_finish(client,saved,decks,user_id)
    heading,action=st.columns([4,1],vertical_alignment='bottom')
    with heading:st.markdown('<p class="study-plan-intro">Plan your Study Mode sessions until your exams and follow your progress.</p>',unsafe_allow_html=True)
    with action:create=st.button('Create study plan',type='primary',icon=':material/add:',use_container_width=True)
    if create:
        st.session_state.plan_draft={'name':'','target':2,'sessions':1,'times':rules.DEFAULT_TIMES[:1],'weekdays_off':[],'dates_off':[],'courses':[]};st.rerun()
    if not data['plans']:
        st.caption('No study plans yet.')
        st.write('**Build a plan in three simple steps**')
        for col,(number,title,detail) in zip(st.columns(3),[
            ('1','Pick courses and exam dates','Choose the decks you want to master and when you want to be ready.'),
            ('2','Set your goal','Choose the learning level each question should reach.'),
            ('3','Get a daily plan','Choose your study days and sessions. You can add the plan to your calendar after saving.'),
        ]):
            with col:
                with st.container(border=True,key='study_plan_empty_step_'+number):
                    st.markdown(f'**{number} · {title}**')
                    st.caption(detail)
    today=date.today()
    for stored in data['plans']:
        plan={**stored['plan'],'id':stored['id']}
        with st.container(border=True,key='study_plan_overview_'+plan['id']):
            title,edit=st.columns([4,1],vertical_alignment='center')
            with title:st.subheader(plan['name'])
            with edit:
                if st.button('Edit',key='plan_edit_'+plan['id'],icon=':material/edit:',use_container_width=True):
                    st.session_state.plan_draft={**plan,'calendar_events':stored.get('calendar_events') or []};st.rerun()
            by_deck={};levels=study_plan_levels(client,plan,decks,by_deck)
            if levels is None:continue
            progress,today_card=st.columns([1.35,.85],vertical_alignment='top')
            with progress:
                st.write('**Progress towards your exams**')
                if len(plan['courses'])>1:
                    everything=[level for item in plan['courses'] for level in levels[item['course']]];overall=rules.plan_progress(everything,plan['target'])
                    st.progress(overall,text=f"Overall progress {overall:.0%}")
                for item in plan['courses']:
                    share=rules.plan_progress(levels[item['course']],plan['target']);st.progress(share,text=f"{item['course']} {share:.0%} · finish by {date.fromisoformat(item['end']):%d %b}")
            with today_card:
                with st.container(border=True,key='study_plan_today_'+plan['id']):
                    study_plan_today(client,plan,levels,by_deck,decks,today,'plan')


def study_design():
    st.html('<style>'+(Path(__file__).parent/'assets'/'study-design.css').read_text()+'</style>')


def study_avatar(kind):
    anonymous=kind=='random'
    settings={**DEFAULT_AVATAR,'skin':'Purple' if anonymous else 'Green','hair':'Side swept','clothing':'Indigo','accessory':'None'}
    encoded=base64.b64encode(render_avatar(settings,anonymous=anonymous)).decode()
    label='Anonymous random partner' if anonymous else 'Study partner avatar'
    question='<span class="study-avatar-question" aria-hidden="true">?</span>' if anonymous else ''
    st.html(f'<div class="study-avatar"><img src="data:image/png;base64,{encoded}" alt="{label}"/>{question}</div>')


def study_choice_cards(key,choices,locked=False):
    selected=st.session_state.get(key,choices[0][0])
    for col,(label,icon,description) in zip(st.columns(len(choices)),choices):
        with col:
            with st.container(border=True,key=key+'_'+icon+('_selected' if selected==label else '')):
                study_avatar(icon)
                if st.button(label,key=key+'_pick_'+icon,type='primary' if selected==label else 'secondary',use_container_width=True,disabled=locked):
                    st.session_state[key]=label;st.session_state.pop('study_join',None);st.rerun()
                st.caption(description)
    return selected


def study_screen(client,profile):
    from uuid import uuid4
    from logic import filter_study_cards
    study_design()
    if st.session_state.get('study_session'):
        st.caption(':material/menu_book: Study Mode · '+st.session_state.get('study_choice','Study alone'))
        study_round_screen(client,st.session_state.study_session);return
    st.html('<style>'+(Path(__file__).parent/'assets'/'play-modes.css').read_text()+'</style>')
    st.markdown((Path(__file__).parent/'assets'/'study-mode.svg').read_text().replace('\n',''),unsafe_allow_html=True)
    st.header('Study Mode')
    st.caption(st.session_state.get('study_choice','Study alone'))
    if st.session_state.get('study_session'):
        study_round_screen(client,st.session_state.study_session);return
    if st.button('Change study mode',icon=':material/arrow_back:'):
        st.session_state.pop('study_active',None);st.session_state.pop('study_choose',None);st.session_state.pop('study_invite_friend',None);st.session_state.pop('play_mode_preview',None);st.rerun()
    data=study_request(client,'list')
    if data is None:return
    # Incoming invitations stay above all setup, regardless of selected course.
    if data['invites']:
        st.subheader('Study invitations')
        for invite in data['invites']:
            with st.container(border=True,key='study_invitation_'+invite['id']):
                study_avatar('friend')
                st.write('**'+invite['username']+' invited you**')
                st.caption(f"{invite['course']} · {invite['language']} · {invite['count']} questions")
                accept,decline=st.columns(2)
                if accept.button('Accept invitation',key='study_accept_'+invite['id'],type='primary'):
                    st.session_state.study_join=invite['id'];st.session_state.study_choice='Study together';st.session_state.study_partner='Friend';st.rerun()
                if decline.button('Decline',key='study_decline_'+invite['id']):
                    if study_request(client,'decline',{'id':invite['id']}) is not None:
                        st.session_state.pop('study_join',None);st.rerun()
    with st.expander('Your saved study sessions',expanded=False):
        if st.button('Refresh study sessions'):st.rerun()
        for s in data['sessions']:
            cols=st.columns([4,1]);cols[0].write(f"**{s['name']}** · {s['mode']} · {s['state']} · {s['count']} questions")
            if s['mode']!='solo':session_partner_chat(client,'study',s['id'],'saved')
            if cols[1].button('Open',key='study_resume_'+s['id']):st.session_state.study_session=s['id'];st.rerun()
            if s['state'] in ('own','waiting') and s['mode']!='solo':
                if st.button('Cancel search / invitation',key='study_cancel_'+s['id']):
                    if study_request(client,'cancel',{'id':s['id']}) is not None:st.rerun()
    choice=st.session_state.get('study_choice','Study alone')
    together=choice=='Study together'
    decks=[dict(d,shared=False) for d in data['decks'] if d.get('language')]
    if not together:decks.extend(dict(d,shared=True) for d in data['shared'])
    if not decks:
        st.info('Create a Study deck in Decks, or set the language of an existing deck first.');return
    offer=next((o for o in data['invites']+data['open'] if o['id']==st.session_state.get('study_join')),None) if together else None
    if offer:
        st.info(f"Joining: {offer['course']} · {offer['language']} · {offer['count']} questions")
        if st.button('Cancel joining and create a new session'):
            st.session_state.pop('study_join',None);st.rerun()
        decks=[d for d in decks if d['course'].strip().casefold()==offer['course'].strip().casefold() and d['language']==offer['language'] and d['count']>=offer['count']//2]
        if not decks:
            st.warning('You need your own compatible deck with enough questions to accept this session. Create one in Decks first.');return
    if not together:study_plan_play_todos(client,data,'solo')
    st.subheader('Your session settings' if offer else 'Create a new study session')
    courses=sorted({d['course'] for d in decks});course=st.selectbox('Study course',courses)
    choices=[d for d in decks if d['course']==course]
    selected_id=st.selectbox('Select quiz deck',[d['id'] for d in choices],format_func=lambda x:next(d['name']+(' · Shared with me' if d['shared'] else '') for d in choices if d['id']==x))
    deck=next(d for d in choices if d['id']==selected_id)
    request={'deck_id':selected_id,'shared':deck['shared']}
    valid=True
    if not together:
        full=study_request(client,'deck',{'id':selected_id,'shared':deck['shared']})
        if full is None:return
        study_progress_summary(full['cards'])
        st.subheader('What do you want to focus on?')
        st.caption('Choose chapters and learning levels to decide which questions you practise. Leave chapters empty to include the full deck; select multiple levels to combine them.')
        chapters=st.multiselect('Chapters / lectures (leave empty for full deck)',sorted({c.get('chapter','') for c in full['cards']}),format_func=lambda x:x or 'General')
        levels=study_level_selector('Learning levels','study_solo_levels')
        eligible=filter_study_cards(full['cards'],chapters,levels);st.caption(f'{len(eligible)} matching questions. No repeats within this session.')
        length=st.radio('Session length',['Choose a number','All matching questions'],horizontal=True)
        count=st.number_input('Number of questions',1,100,min(10,max(1,len(eligible)))) if length=='Choose a number' else 0
        valid=bool(eligible) and (count==0 or count<=len(eligible))
        request.update(mode='solo',count=count,chapters=chapters,levels=levels)
    else:
        st.caption('Answer your own half first, then your partner’s. No timer per question. After matching, both players have 24 hours to finish.')
        opponent=study_choice_cards('study_partner',[('Random player','random','Meet someone studying your course.'),('Friend','friend','Practise with someone you know.')],locked=bool(offer))
        mode='random' if opponent=='Random player' else 'friend';request['mode']=mode
        if offer:
            count=offer['count'];request['join_id']=offer['id']
            st.caption('Confirm below to reserve this session. You answer your own questions first.')
        else:
            count=20
            if mode=='friend':
                options=study_request(client,'friend_options',{'deck_id':selected_id})
                if options is None:return
                friends=options['friends']
                if not friends:
                    if not data['friends']:
                        st.info('You don’t have any friends yet. Add a friend to study together.')
                        st.caption('This opens the Friends menu. Use Back to Study Together there to return to these settings.')
                        if st.button('Go to Friends',icon=':material/person_add:'):
                            st.session_state.study_return_after_friends=True
                            navigate('Friends');st.rerun()
                    else:st.info('None of your friends have this course and deck language in their profile yet. Ask a friend to add them to study together.')
                    valid=False
                else:
                    friend_ids=[f['id'] for f in friends]
                    requested_friend=st.session_state.get('study_invite_friend',{})
                    requested_id=requested_friend.get('id')
                    if requested_id and requested_id not in friend_ids:
                        st.warning(f"{requested_friend.get('username','This friend')} is not eligible for the selected course and language. Choose another friend or update the session settings.")
                    index=friend_ids.index(requested_id) if requested_id in friend_ids else 0
                    friend=st.selectbox('Choose a friend',friend_ids,index=index,format_func=lambda x:next(f['username'] for f in friends if f['id']==x))
                    request['friend_id']=friend
                    st.caption('Only friends enrolled in this course and speaking the deck language are shown.')
                st.caption('Your invitation is sent after you finish your own half. Your friend must accept.')
            else:
                st.caption('Only students who also choose random study can match. Your search lasts 24 hours after your own half.')
                offers=[o for o in data['open'] if o['course'].strip().casefold()==course.strip().casefold() and o['language']==deck['language']]
                with st.expander('Discover open study sessions',expanded=bool(offers)):
                    if not offers:st.caption('No open sessions for this course yet. Be the first to start one.')
                    for available in offers:
                        cols=st.columns([3,1]);cols[0].write(f"**{available['count']} questions** · {available['course']}")
                        if cols[1].button('Join',key='study_join_'+available['id']):
                            st.session_state.study_join=available['id'];st.rerun()
        if not offer:count=st.selectbox('Total questions',[20,40,60,80,100])
        st.info(f'{count} questions = {count//2} from your deck + {count//2} from your partner’s deck.')
        st.caption(f'First, answer {count//2} questions from your own deck. Once a partner is matched or your friend accepts, answer their {count//2} questions. Both of you answer the same combined set, starting with your own half. You can leave and return while waiting.')
        full=study_request(client,'deck',{'id':selected_id})
        if full is None:return
        st.subheader('What do you want to focus on?')
        st.caption('Choose the learning levels to prioritise in your half of the session. If there are not enough, we fill the remaining places with other questions from your deck, without repeats.')
        levels=study_level_selector('Preferred learning levels','study_together_levels')
        request['levels']=levels
        preferred=len(filter_study_cards(full['cards'],[],levels))
        needed=max(0,count//2-preferred)
        st.caption('These preferences choose your half only. They do not restrict who you can match with. Your partner chooses their half separately; both players then answer exactly the same combined questions.')
        if not levels:st.warning('Choose at least one preferred learning level.');valid=False
        elif needed and deck['count']>=count//2:st.info(f'{preferred} questions match your preferred levels. The remaining {needed} in your half will be randomly selected from your other questions, without repeats.')
        request['count']=count
        if deck['count']<count//2:st.warning(f"This session needs at least {count//2} questions in your deck; it currently has {deck['count']}.");valid=False
        consent=st.checkbox('I agree to share this version of my full deck with a partner who finishes, even if I do not finish.')
        st.caption('Finish to receive their full deck. Later edits are never shared with the received copy. Learning progress and private notes stay private.')
        request['consent']=consent;valid=valid and consent
    if st.button('Start studying',type='primary',disabled=not valid):
        if 'study_request_id' not in st.session_state:st.session_state.study_request_id=str(uuid4())
        request['request_id']=st.session_state.study_request_id
        r=study_request(client,'start',request)
        if r is not None:
            st.session_state.study_session=r['id'];st.session_state.pop('study_request_id',None);st.session_state.pop('study_invite_friend',None);st.rerun()


def ongoing_sessions(client):
    from db import BattleRepository
    from logic import battle_session_groups
    battle_data=play_request(BattleRepository(client),'list')
    study_data=study_request(client,'list')
    st.subheader('Ongoing sessions')
    battle,study=st.columns(2)
    with battle:
        st.markdown('**:material/swords: Battle**')
        data=battle_data
        if data is not None:
            active=battle_session_groups(data.get('sessions',[]))['ongoing']
            if not active:st.caption('No ongoing Battle sessions.')
            for session in active:
                with st.container(border=True):
                    st.write('**'+session['deck_name']+'**')
                    st.caption(f"{session['course']} · {session['language']} · 15 questions · {session['status'].title()}")
                    if session['status']=='pending':st.caption('Your answers are saved. Waiting for your opponent.')
                    if st.button('Resume Battle' if session.get('started') else 'Start Battle',key='home_battle_'+session['id']):
                        st.session_state.battle_session=session['id'];st.session_state.pop('battle_feedback',None);st.rerun()
    with study:
        st.markdown('**:material/menu_book: Study**')
        data=study_data
        if data is not None:
            active=[s for s in data['sessions'] if s['state'] in ('own','waiting','paired')]
            if not active:st.caption('No ongoing Study sessions.')
            for session in active:
                with st.container(border=True):
                    st.write('**'+session['name']+'**')
                    if session['mode']!='solo':session_partner_chat(client,'study',session['id'],'home')
                    st.caption(('Study alone' if session['mode']=='solo' else 'Study together')+f" · {session['cursor']} / {session['count']} answered")
                    if session['state']=='waiting':st.caption('Waiting for a study partner.')
                    if session.get('deadline'):st.caption('Finish by '+session['deadline'])
                    if st.button('Open Study' if session['state']=='waiting' else 'Resume Study',key='home_study_'+session['id']):
                        st.session_state.study_active=True;st.session_state.study_choice='Study alone' if session['mode']=='solo' else 'Study together';st.session_state.study_session=session['id'];st.rerun()
            study_plan_play_todos(client,data)

    st.subheader('Session history')
    battle_history,study_history=st.columns(2)
    with battle_history:
        st.markdown('**:material/swords: Battle**')
        finished=battle_session_groups((battle_data or {}).get('sessions',[]))['completed']
        if not finished:st.caption('No past Battle sessions yet.')
        for session in finished:
            with st.container(border=True):
                st.write('**'+session['deck_name']+'**')
                st.caption('Opponent: '+session.get('opponent_username','Unknown opponent'))
                st.caption(f"{session['course']} · {session['language']} · Completed · {session.get('result','').title()} · {session.get('game_xp_delta',0):+d} Battle XP · {session['score']}/15")
                if st.button('Review Battle',key='history_battle_review_'+session['id']):
                    battle_review_dialog(client,session['id'])
    with study_history:
        st.markdown('**:material/menu_book: Study**')
        finished=[s for s in (study_data or {}).get('sessions',[]) if s['state'] not in ('own','waiting','paired')]
        if not finished:st.caption('No past Study sessions yet.')
        for session in finished:
            with st.container(border=True):
                st.write('**'+session['name']+'**')
                if session['mode']!='solo':session_partner_chat(client,'study',session['id'],'history')
                st.caption(('Study alone' if session['mode']=='solo' else 'Study together')+' · '+session['state'].capitalize()+f" · {session['cursor']} / {session['count']} answered")
                if st.button('View Study session',key='history_study_'+session['id']):
                    st.session_state.study_active=True;st.session_state.study_session=session['id'];st.rerun()


def battle_request(client,action,data=None):
    from db import BattleRepository
    return play_request(BattleRepository(client),action,data)


def battle_deck_availability(client,course,language):
    from db import BattleRepository
    repository=BattleRepository(client)
    # Streamlit can hot-reload app.py before an imported adapter module. Reload
    # only when the running worker still has the previous adapter shape.
    if not hasattr(repository,'availability'):repository=fresh_module('db').BattleRepository(client)
    try:return repository.availability(course,language)
    except ValueError as exc:st.error(str(exc));return None


def battle_cancel_search(client):
    from db import BattleRepository
    repository=BattleRepository(client)
    if not hasattr(repository,'cancel_search'):repository=fresh_module('db').BattleRepository(client)
    try:return repository.cancel_search()
    except ValueError as exc:st.error(str(exc));return None


def battle_progress(client,session_id):
    from db import BattleRepository
    try:return BattleRepository(client).progress(session_id)
    except ValueError as exc:st.error(str(exc));return None


def battle_overview(answers,current_index):
    from battle_ui import battle_progress_tiles
    symbols={'correct':'✓','incorrect':'×','current':'•','open':''}
    tiles=battle_progress_tiles(answers,current_index)
    markup=''.join(f'<span class="battle-tile battle-tile-{tile["state"]}" aria-label="Question {tile["number"]}: {tile["state"]}">{symbols[tile["state"]] or tile["number"]}</span>' for tile in tiles)
    st.html('<aside class="battle-overview"><h3>Overview</h3><div class="battle-overview-grid">'+markup+'</div><div class="battle-legend"><span><i class="correct"></i>Correct</span><span><i class="incorrect"></i>Incorrect or time expired</span></div></aside>')


def battle_timer(seconds):
    from battle_ui import timer_tick_fractions
    start,end=timer_tick_fractions(seconds);urgent=' urgent' if seconds<=10 else ''
    st.html(f'<div class="battle-timer-track" role="progressbar" aria-label="Time remaining" aria-valuemin="0" aria-valuemax="30" aria-valuenow="{seconds}"><div class="battle-timer-fill{urgent}" style="--timer-start:{start*100:.3f}%;--timer-end:{end*100:.3f}%"></div></div><p class="battle-timer-label">{seconds} seconds remaining · the timer continues if you leave this Battle.</p>')


@st.dialog('Battle review',width='large')
def battle_review_dialog(client,session_id):
    result=battle_request(client,'review',{'id':session_id})
    if result is None:return
    st.metric('Correct answers',f"{result['score']} / 15")
    for number,card in enumerate(result['cards'],1):
        answer=next((item for item in result['answers'] if item['index']==number-1),None)
        with st.expander(f"Question {number}: {card['question']}"):
            if answer is None:st.caption('Not answered')
            elif answer.get('timed_out'):st.caption('Time expired')
            elif answer.get('correct'):st.success('Correct')
            else:st.error('Incorrect')
            for option in card['answers']:
                label=option['text']+(' — Your answer' if answer and answer.get('answer_id')==option['id'] else '')
                if option['id']==card['correct_answer_id']:st.success(label+' — Correct answer')
                else:st.write(label)
            with st.popover('Report this question',key=f'battle_report_question_{session_id}_{number}'):
                battle_question_report_form(client,session_id,number-1)


def battle_question_report_form(client,session_id,card_index):
    from db import BattleRepository
    report_key=f'battle_question_reported_{session_id}_{card_index}'
    if st.session_state.get(report_key):
        st.success('This question has been reported. Thank you.')
        return
    labels={
        'incorrect_answer':'Incorrect answer',
        'unclear_question':'Question is unclear',
        'other':'Other',
    }
    reason=st.selectbox('Reason',list(labels),format_func=labels.get,key=f'battle_report_reason_{session_id}_{card_index}')
    note=st.text_area('Optional comment',max_chars=500,key=f'battle_report_note_{session_id}_{card_index}')
    if st.button('Submit report',type='primary',key=f'battle_submit_report_{session_id}_{card_index}'):
        try:result=BattleRepository(client).report_question(session_id,card_index,reason,note)
        except ValueError as exc:st.error(str(exc))
        else:
            st.session_state[report_key]=True
            st.success('Thank you. This question has been reported.' if result.get('reported') else 'This question was already reported.')


@st.fragment(run_every='1s')
def battle_round_screen(client,session_id):
    st.html('<style>'+ (Path(__file__).parent/'assets'/'battle-round.css').read_text()+'</style>')
    progress=battle_progress(client,session_id)
    if progress is None:return
    answers=progress.get('answers',[])
    feedback=st.session_state.get('battle_feedback')
    if feedback and feedback.get('id')==session_id:
        card=feedback['card'];response=feedback['feedback']
        question,overview=st.columns([3,1],gap='large')
        with question:
            st.caption(f"Question {response['index']+1} of 15")
            st.html('<div class="battle-question-card">'+escape(card['question'])+'</div>')
            if response['correct']:st.success('Correct!')
            elif response.get('timed_out'):st.error('Time expired.')
            else:st.error('That answer was incorrect.')
            answer_markup=''.join('<div class="battle-answer-card '+('is-correct is-correct-animated' if answer['id']==card['correct_answer_id'] and response['correct'] else 'is-correct' if answer['id']==card['correct_answer_id'] else 'is-incorrect' if answer['id']==response.get('answer_id') else 'is-neutral')+'">'+escape(answer['text'])+'</div>' for answer in display_options(card['answers'],session_id,response['index']))
            st.html('<div class="battle-answer-grid">'+answer_markup+'</div>')
            if st.button('Continue',type='primary'):
                st.session_state.pop('battle_feedback',None);st.rerun()
        with overview:battle_overview(answers,response['index']+1)
        return
    result=battle_request(client,'round',{'id':session_id})
    if result is None:return
    state=result['state']
    if state=='feedback':
        st.session_state.battle_feedback={**result,'id':session_id};st.rerun()
    if state=='question':
        question,overview=st.columns([3,1],gap='large')
        with question:
            st.caption(f"Question {result['index']+1} of 15")
            st.html('<div class="battle-question-card">'+escape(result['question'])+'</div>')
            question_tools(f'battle_{session_id}_{result["index"]}',result.get('allow_calculator') is True)
            columns=st.columns(2)
            for i,answer in enumerate(display_options(result['options'],session_id,result['index'])):
                if columns[i%2].button(answer['text'],key=f'battle_answer_{session_id}_{result["index"]}_{answer["id"]}',use_container_width=True):
                    response=battle_request(client,'answer',{'id':session_id,'index':result['index'],'answer_id':answer['id']})
                    if response is not None:
                        st.session_state.battle_feedback={**response,'id':session_id};st.rerun()
            battle_timer(result['seconds'])
        with overview:battle_overview(answers,result['index'])
        return
    if state=='finish':
        st.metric('Correct answers',f"{result['score']} / 15")
        if st.button('Finish Battle',type='primary'):
            if battle_request(client,'finish',{'id':session_id}) is not None:st.rerun()
        return
    if state=='rating':
        st.subheader('Battle round finished')
        st.metric('Correct answers',f"{result['score']} / 15")
        if result.get('can_rate'):
            rating=st.radio('How was this Battle Deck?',('good','neutral','bad'),format_func=lambda value:{'good':'Good','neutral':'Neutral','bad':'Bad'}[value],horizontal=True)
            if st.button('Save rating',type='primary'):
                if battle_request(client,'rate',{'id':session_id,'rating':rating}) is not None:
                    st.session_state.pop('battle_session',None);st.session_state.pop('battle_feedback',None);st.session_state.main_page='Play';st.rerun()
        else:st.info('You played your own Battle Deck. It does not receive a rating from you.')
        if st.button('Back to Battle Mode'):
            st.session_state.pop('battle_session',None);st.rerun()
        return
    st.info('This Battle is complete.')
    if st.button('Back to Battle Mode'):st.session_state.pop('battle_session',None);st.rerun()


@st.dialog('Battle Mode',width='large')
def battle_game_dialog(client,session_id):
    if st.button('Save and leave Battle'):
        st.session_state.pop('battle_session',None);st.rerun()
    battle_round_screen(client,session_id)


@st.fragment(run_every='1s')
def battle_pending_search(client,search):
    from logic import battle_search_remaining_seconds,battle_search_timer_text
    remaining=battle_search_remaining_seconds(search.get('expires_at'))
    last_check=st.session_state.get('battle_search_status_checked_at',0)
    if remaining==0:
        refreshed=battle_request(client,'list')
        st.session_state.battle_search_status_checked_at=time.monotonic()
        if refreshed is not None and not refreshed.get('search'):
            st.rerun()
        st.caption('No pending Battles.')
        return
    if time.monotonic()-last_check>=10:
        refreshed=battle_request(client,'list')
        st.session_state.battle_search_status_checked_at=time.monotonic()
        if refreshed is not None and not refreshed.get('search'):st.rerun()
    with st.container(border=True):
        st.write('**Finding an opponent**')
        st.caption(f"{search['course']} · {search['language']}")
        st.write('**Time remaining: '+battle_search_timer_text(remaining)+'**')
        st.progress(min(1,remaining/3600),text='Searching for a compatible player')
        if st.button('Cancel search',key='battle_cancel_search'):
            if battle_cancel_search(client) is not None:
                st.session_state.battle_notice='Battle search cancelled.'
                st.rerun()


def battle_session_overview(client,sessions,search=None):
    groups=(('Ongoing','ongoing'),('Pending','pending'),('Completed','completed'))
    for column,(label,status) in zip(st.columns(3),groups):
        with column:
            st.markdown('**'+label+'**')
            rows=[session for session in sessions if session['status']==status]
            if not rows and not (status=='pending' and search):
                st.caption('No '+label.lower()+' Battles.')
            if status=='pending' and search:battle_pending_search(client,search)
            for session in rows:
                with st.container(border=True):
                    opponent=session.get('opponent_username','Unknown opponent')
                    st.write('**'+session['deck_name']+'**')
                    opponent_result=(' · '+str(session['opponent_score'])+' / 15 correct' if status=='completed' and session.get('opponent_score') is not None else '')
                    st.caption('vs. '+opponent+opponent_result)
                    if status=='ongoing':
                        st.caption('Your turn')
                        if st.button('Resume Battle' if session.get('started') else 'Start Battle',key='overview_battle_'+session['id'],type='primary'):
                            st.session_state.battle_session=session['id'];st.session_state.pop('battle_feedback',None);st.rerun()
                    elif status=='pending':
                        st.caption(f"Your result: {session['score']} / 15")
                        st.caption('Waiting for '+opponent+'.')
                    else:
                        if session.get('opponent_score') is None:
                            st.write(f"**Your correct answers: {session['score']} / 15 · {session.get('result','').title()}**")
                        else:
                            st.write(f"**Your correct answers: {session['score']} / 15 · {session.get('result','').title()}**")
                        st.caption(f"{session.get('game_xp_delta',0):+d} Battle XP")
                        if st.button('Review Battle',key='overview_battle_review_'+session['id']):battle_review_dialog(client,session['id'])


def battle_new_setup_screen(client,profile):
    st.subheader('Start a new Battle')
    if st.button('Back to Game Overview',key='close_new_battle',icon=':material/arrow_back:'):
        st.session_state.pop('battle_new_setup',None);st.session_state.pop('battle_invite_friend',None);st.rerun()
    course=st.selectbox('Course',profile['courses'],key='battle_course')
    language=st.selectbox('Language',profile['languages'],key='battle_language')
    source=st.radio('Battle Deck source',('Random Deck','Top Decks'),horizontal=True)
    selected=None
    availability=None
    if source=='Top Decks':
        top=battle_request(client,'top',{'course':course,'language':language})
        ranked=(top or {}).get('decks',[])
        if ranked:
            labels={item['id']:f"{item['name']} · {item['score']:+d} today · {item['rating_count']} ratings" for item in ranked}
            selected=st.selectbox('Top Deck',list(labels),format_func=labels.get)
        else:st.info('No Top Deck qualifies today yet.')
        for position in range(len(ranked)+1,11):st.button(f'{position}. Outstanding',disabled=True,key='battle_outstanding_'+str(position),use_container_width=True)
    else:
        availability=battle_deck_availability(client,course,language)
        if availability is not None and not availability['available']:
            st.warning('No available Battle Decks yet for the selected course and language. Create a Battle Deck first or choose different criteria.')
        elif availability is not None:
            st.caption('The server will choose an eligible public 15-question Battle Deck uniformly after it finds a compatible opponent.')
    opponent=st.radio('Opponent',('Random player','Friend'),horizontal=True)
    payload={'course':course,'language':language,'source_kind':'random' if source=='Random Deck' else 'top'}
    if selected:payload['deck_id']=selected
    can_start=not (source=='Random Deck' and (availability is None or not availability['available']))
    if opponent=='Random player':
        if st.button('Find random player',type='primary',disabled=not can_start or (source=='Top Decks' and selected is None)):
            result=battle_request(client,'join',payload)
            if result is not None:
                if result.get('session_id'):st.session_state.battle_session=result['session_id']
                else:
                    st.session_state.battle_notice='We are searching for a compatible opponent for up to 1 hour. Your request now appears under Pending.'
                    st.session_state.pop('battle_new_setup',None)
                st.rerun()
    else:
        friend_options=battle_request(client,'friend_options',{'course':course,'language':language})
        friends=(friend_options or {}).get('friends',[])
        if not friends:st.info('No accepted friend currently has this course and language at your university.')
        else:
            friend_ids=[friend['id'] for friend in friends]
            requested_friend=st.session_state.get('battle_invite_friend',{})
            requested_id=requested_friend.get('id')
            if requested_id and requested_id not in friend_ids:
                st.warning(f"{requested_friend.get('username','This friend')} is not eligible for the selected course and language. Choose another friend or change the Battle settings.")
            index=friend_ids.index(requested_id) if requested_id in friend_ids else 0
            friend_id=st.selectbox('Friend',friend_ids,index=index,format_func=lambda value:next(friend['username'] for friend in friends if friend['id']==value))
            if st.button('Send Battle invitation',type='primary',disabled=not can_start or (source=='Top Decks' and selected is None)):
                result=battle_request(client,'invite',{**payload,'friend_id':friend_id})
                if result is not None:
                    st.session_state.pop('battle_invite_friend',None)
                    st.success(result.get('message','Battle invitation sent.'))


def battle_screen(client,profile):
    st.subheader('Battle Mode')
    st.caption('15 shared questions · 30 seconds per question · Battle XP · Battle never changes Study progress.')
    if st.session_state.get('battle_session'):
        battle_game_dialog(client,st.session_state.battle_session);return
    if st.session_state.get('battle_new_setup'):
        battle_new_setup_screen(client,profile);return
    state=battle_request(client,'list')
    if state is None:return
    title,action=st.columns([4,1],vertical_alignment='center')
    with title:st.subheader('Game Overview')
    with action:
        if st.button('New Battle',key='open_new_battle',type='primary',use_container_width=True):
            st.session_state.battle_new_setup=True;st.rerun()
    if notice:=st.session_state.pop('battle_notice',None):st.success(notice)
    battle_session_overview(client,state.get('sessions',[]),state.get('search'))
    if state.get('invites'):
        st.subheader('Battle invitations')
        for invite in state['invites']:
            with st.container(border=True):
                st.write(('From ' if invite['incoming'] else 'To ')+invite['username'])
                deck_name=invite.get('deck_name') or 'Random Deck'
                st.caption(f"{deck_name} · {invite['course']} · {invite['language']}")
                if invite['incoming']:
                    accept,decline=st.columns(2)
                    if accept.button('Accept',key='battle_accept_'+invite['id']):
                        result=battle_request(client,'accept_invite',{'invite_id':invite['id']})
                        if result is not None:st.session_state.battle_session=result['session_id'];st.rerun()
                    if decline.button('Decline',key='battle_decline_'+invite['id']):
                        if battle_request(client,'decline_invite',{'invite_id':invite['id']}) is not None:st.rerun()
                elif st.button('Cancel invitation',key='battle_cancel_'+invite['id']):
                    if battle_request(client,'cancel_invite',{'invite_id':invite['id']}) is not None:st.rerun()


LEADERBOARD_STYLE='<style>.sd-lb-row{display:flex;align-items:center;gap:12px;padding:8px 12px;border-top:1px solid var(--sd-border)}.sd-lb-row img{width:40px;height:40px;border-radius:50%;object-fit:cover}.sd-lb-place{width:44px}.sd-lb-name{flex:1}.sd-lb-xp{white-space:nowrap}.sd-lb-me{background:var(--sd-hover);border-radius:12px;font-weight:700}</style>'

def leaderboard_rows(rows,repo):
    lines='';cache=st.session_state.setdefault('leaderboard_pictures',{})
    for row in rows:
        path=row.get('image_path')
        if path not in cache:
            try:
                data=repo.image(path);cache[path]=data if isinstance(data,(bytes,bytearray)) else None
            except Exception:cache[path]=None
        image=base64.b64encode(cache[path] or render_avatar(row.get('avatar') or DEFAULT_AVATAR)).decode()
        lines+=f'<div class="sd-lb-row{" sd-lb-me" if row.get("me") else ""}"><span class="sd-lb-place">#{int(row["rank"])}</span><img src="data:image/png;base64,{image}" alt=""><span class="sd-lb-name">{escape(str(row["username"]))}{" (you)" if row.get("me") else ""}</span><span class="sd-lb-xp">{int(row["xp"])} XP</span></div>'
    st.html(LEADERBOARD_STYLE+'<div>'+lines+'</div>')

def leaderboard_demo(profile):
    names=['nora_k','tiago','lena_m','felix','ines','jonas','sofia_r','matteo','clara','diogo','emma_w','lukas','beatriz','hugo','anna_s'];points=[1840,1675,1520,1520,1390,1210,1085,960,870,790,640,455,320,180,60]
    rows=[{'username':n,'xp':x,'image_path':None,'me':False} for n,x in zip(names,points)]+[{'username':profile['username'],'xp':705,'image_path':profile.get('image_path'),'me':True}]
    def ranked(items):return [{**item,'rank':1+sum(other['xp']>item['xp'] for other in items)} for item in sorted(items,key=lambda item:(-item['xp'],item['username']))]
    world=ranked(rows);return {'top':world[:10],'me':next(item for item in world if item['me']),'friends':ranked([item for item in rows if item['me'] or item['username'] in ('tiago','ines','emma_w','hugo')])}

def leaderboard_screen(client,repo,profile=None):
    from db import LeaderboardRepository
    st.title('Leaderboard')
    if profile and os.getenv('LEADERBOARD_DEMO')=='1' and (os.getenv('APP_URL') or '').startswith('http://localhost'):
        st.warning('Preview with invented students and XP.');data=leaderboard_demo(profile)
    else:
        try:data=LeaderboardRepository(client).load()
        except ValueError as exc:st.error(str(exc));return
    st.caption('Ranks are based on Battle XP earned in Battle Mode. Study Mode does not affect them.')
    global_tab,friends_tab=st.tabs(['Global top 10','Friends'])
    for tab,rows in ((global_tab,data.get('top',[])),(friends_tab,data.get('friends',[]))):
        with tab:
            leaderboard_rows(rows,repo)
            if tab is global_tab and data.get('me') and not any(row.get('me') for row in rows):
                st.caption('Your place')
                leaderboard_rows([data['me']],repo)
            if tab is friends_tab and len(rows)<2:st.caption('Add friends to compare your Battle XP.')


def play_screen(client,profile):
    from db import PlayRepository
    st.title('Play')
    if st.session_state.get('study_active'):
        study_screen(client,profile);return
    if st.session_state.get('play_duel'):
        if st.button('Exit round'):
            st.session_state.play_exit_to='Play';st.rerun()
        play_round_screen(client,st.session_state.play_duel)
    elif st.session_state.get('play_review'):
        if st.button('Back to Play'):
            st.session_state.pop('play_review',None);st.rerun()
        result=play_request(PlayRepository(client),'review',{'duel_id':st.session_state.play_review})
        if result:
            for i,card in enumerate(result['cards']):
                with st.expander(f"Question {i+1}: {card['question']}"):
                    response=next((a for a in result['answers'] if a['index']==i),None)
                    st.caption('Not answered' if response is None else 'Time expired' if response['timed_out'] else 'Correct' if response['correct'] else 'Incorrect')
                    for a in card['answers']:
                        label=a['text']+(' — Your answer' if response and response['answer_id']==a['id'] else '')
                        if a['id']==card['correct_answer_id']:st.success(label+' — Correct answer')
                        else:st.write(label)
    else:
        assets=Path(__file__).parent/'assets'
        st.html('<style>'+ (assets/'play-modes.css').read_text()+'</style>')
        selected=st.session_state.get('play_mode_preview')
        if not selected:
            st.subheader('Create new session')
            st.write('Choose how you want to play.')
            battle,study=st.columns(2)
            with battle:
                with st.container(border=True,key='battle_mode_card'):
                    st.markdown((assets/'battle-mode.svg').read_text().replace('\n',''),unsafe_allow_html=True)
                    st.subheader('Battle Mode')
                    st.caption('Compete, test your knowledge and earn XP · 15 questions.')
                    if st.button('Battle Mode',key='choose_battle_mode',use_container_width=True):
                        st.session_state.play_mode_preview='Battle';st.rerun()
            with study:
                with st.container(border=True,key='study_mode_card'):
                    st.markdown((assets/'study-mode.svg').read_text().replace('\n',''),unsafe_allow_html=True)
                    st.subheader('Study Mode')
                    st.caption('Practise together and focus on learning.')
                    if st.button('Study Mode',key='choose_study_mode',type='primary',use_container_width=True):
                        st.session_state.play_mode_preview='Study';st.rerun()
        elif selected=='Battle':
            battle_screen(client,profile);return
        else:
            st.header('Study Mode')
            st.caption('Practise together and focus on learning.')
            study_design()
            st.caption('How would you like to study?')
            for col,(label,icon,material) in zip(st.columns(2),[('Study alone','solo',':material/person:'),('Study together','together',':material/group:')]):
                with col:
                    if st.button(label,key='enter_'+icon,icon=material,use_container_width=True):
                        st.session_state.study_choice=label;st.session_state.study_active=True;st.session_state.pop('study_session',None);st.session_state.pop('study_join',None);st.rerun()
            if st.button('Change play mode',icon=':material/arrow_back:'):
                st.session_state.pop('play_mode_preview',None);st.rerun()
        st.divider()
        ongoing_sessions(client)


def config(key):
    if os.getenv(key):return os.getenv(key)
    try:return st.secrets.get(key,"")
    except FileNotFoundError:return ""
try:
    url=config("SUPABASE_URL");key=config("SUPABASE_PUBLISHABLE_KEY")
except Exception:
    url=key=""
if not url or not key:
    st.info("UniArena is waiting for its Supabase connection. Add the project URL and publishable key to .streamlit/secrets.toml.")
    st.stop()
if "auth" not in st.session_state:
    try:
        # AI question generation calls an external provider and commonly takes
        # longer than the default Functions client read timeout.
        client=create_client(url,key,options=ClientOptions(auto_refresh_token=False,persist_session=True,function_client_timeout=60))
        st.session_state.auth=AuthService(client,app_url=config("APP_URL") or "http://localhost:8501")
    except Exception:
        st.error("Could not connect to UniArena. Please try again shortly.")
        st.stop()
auth=st.session_state.auth
# Upgrade an existing session safely when Streamlit hot-reloads a deployment.
if not hasattr(auth,"resumable_session"):
    previous=auth
    auth=AuthService(previous.client,app_url=previous.app_url)
    auth.user=previous.user
    auth.recovery_verified=previous.recovery_verified
    st.session_state.auth=auth
# Recovery tokens are received once from the email redirect and verified by Supabase.
if not st.session_state.get("recovery_received"):
    recovery_data=recovery_callback()
    if recovery_data:
        st.session_state.recovery_received=True
        result=auth.begin_recovery(recovery_data)
        if result.status=="recovery_ready":
            st.session_state.recovering=True
        else:
            st.session_state.recovery_error=result.message
        st.rerun()
if st.session_state.get("recovering"):
    st.title("Choose a new password")
    with st.form("new_password"):
        new_password=st.text_input("New password",type="password")
        confirm_password=st.text_input("Confirm new password",type="password")
        update=st.form_submit_button("Update password",type="primary")
    if update:
        result=auth.update_password(new_password,confirm_password)
        if result.status=="password_updated":
            for state_key in list(st.session_state):del st.session_state[state_key]
            st.session_state.browser_loaded=True
            st.session_state.started=True
            st.session_state.notice=result.message
            st.rerun()
        else:st.error(result.message)
    if st.button("Back to sign in"):
        auth.sign_out()
        for state_key in list(st.session_state):del st.session_state[state_key]
        st.session_state.browser_loaded=True
        st.session_state.started=True
        st.rerun()
    st.stop()
if st.session_state.get("recovery_error"):
    st.error(st.session_state.recovery_error)
# Read browser state once per server session. Never trust a stored user ID.
if not st.session_state.get("browser_loaded"):
    saved=browser_bridge("read")
    if saved is None:
        st.caption("Opening UniArena…")
        st.stop()
    saved=saved if isinstance(saved,dict) else {}
    st.session_state.browser_loaded=True
    st.session_state.started=bool(saved.get("started")) or bool(auth.user)
    if "account_mode" not in st.session_state and saved.get("mode") in ("Sign in","Create account"):
        st.session_state.account_mode=saved["mode"]
    if not auth.user and not st.session_state.get("recovery_error") and saved.get("session"):
        if auth.restore_session(saved["session"]):
            if saved.get("user_id")==auth.user.id:
                st.session_state.editing=saved.get("route")=="edit"
                st.session_state.main_page=saved.get("page") if saved.get("page") in ("Decks","Play","Friends","Leaderboard","Study Plan","Profile") else "Play"
                if isinstance(saved.get("deck_open"),str):st.session_state.deck_open=saved["deck_open"]
            st.session_state.started=True
        else:
            st.session_state.started=True
            st.session_state.notice="Please sign in again to continue. Your saved profile is still here."
    st.rerun()
# Confirm the signed-in user with Supabase at most once a minute; token refresh still runs on every interaction below.
verification_due=bool(auth.user) and page_speed.should_verify(time.time(),st.session_state.get("verified_at"))
if verification_due and auth.verify():st.session_state.verified_at=time.time()
elif verification_due:
    for k in list(st.session_state):
        if k!="auth": del st.session_state[k]
    st.session_state.browser_loaded=True
    st.session_state.started=True
    st.warning("Your session has ended. Please sign in again.")
browser_bridge("write",{
    "started":bool(st.session_state.get("started") or auth.user),
    "mode":st.session_state.get("account_mode","Sign in"),
    "route":"edit" if st.session_state.get("editing") else "profile",
    "page":st.session_state.get("main_page","Play"),
    "deck_open":st.session_state.get("deck_open"),
    "user_id":auth.user.id if auth.user else None,
    "session":auth.resumable_session(),
})
if not auth.user and not st.session_state.get("started") and not st.session_state.get("pending_invite") and not st.session_state.get("recovery_error"):
    if welcome(logo_data):
        st.session_state.started=True
        st.rerun()
    st.stop()
if not auth.user:
    st.html(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px"><img src="data:image/png;base64,{logo_small}" alt="UniArena logo: two flashcards in an arena" style="width:112px;height:70px;object-fit:contain"><span style="font-size:36px;font-weight:800;letter-spacing:-1.5px;color:var(--sd-text)">Uni<span style="color:var(--sd-accent)">Arena</span></span></div>')
    st.caption("A little competition. A lot of learning.")
notice=st.session_state.pop("notice",None)
if notice: st.success(notice)

if not auth.user:
    if st.session_state.get("pending_invite"):st.info("You have a friend invitation. Sign in or create an account, then accept it after completing your profile.")
    st.title("Your next study win starts here.")
    st.write("Create your student profile. Build your knowledge, then challenge your friends.")
    mode=st.segmented_control("Account",["Sign in","Create account"],default=None if "account_mode" in st.session_state else "Sign in",key="account_mode")
    if st.session_state.pop("clear_account_passwords",False):
        st.session_state["account_password"]=""
        st.session_state["account_confirmation"]=""
    with st.form("account",clear_on_submit=False):
        username=None
        username_error=None
        if mode=="Create account":
            username=st.text_input("Username",key="account_username")
            st.caption("3–24 letters, numbers or underscores. No spaces. Your username is visible to other students.")
            username_error=st.empty()
        email=st.text_input("Email",placeholder="you@university.edu",key="account_email")
        password=st.text_input("Password",type="password",key="account_password")
        confirmation=st.text_input("Confirm password",type="password",key="account_confirmation") if mode=="Create account" else None
        submitted=st.form_submit_button(mode or "Sign in",type="primary",use_container_width=True)
    if submitted:
        if mode=="Create account":
            try: validate_username(username)
            except ValueError as exc:
                username_error.error(str(exc))
                st.markdown("<style>.st-key-account_username input{border:2px solid #D84550!important}</style>",unsafe_allow_html=True)
                st.stop()
            result=auth.sign_up(email,password,confirmation,username,st.session_state.get("pending_invite"))
        else: result=auth.sign_in(email,password)
        if result.status in ("signed_in","check_email"):
            st.session_state.clear_account_passwords=True
            st.session_state.notice=result.message
            st.rerun()
        else:st.error(result.message)
    if mode=="Sign in":
        with st.expander("Forgot password?"):
            st.write("Enter your email and we’ll send you a password reset link.")
            with st.form("forgot_password"):
                reset_email=st.text_input("Account email",value=email)
                send_reset=st.form_submit_button("Send reset link")
            if send_reset:
                result=auth.request_password_reset(reset_email)
                if result.status=="check_email":st.success(result.message)
                else:st.error(result.message)
    st.caption("Your email stays private. You’ll confirm it before signing in.")
    if st.button("View welcome screen"):
        st.session_state.started=False
        st.rerun()
    st.stop()

for credential_key in ("account_password","account_confirmation"):
    st.session_state.pop(credential_key,None)
repo=ProfileRepository(auth.client,auth.user.id)
profile_cache=st.session_state.setdefault("profile_cache",page_speed.ProfileCache())
# Always read fresh where the profile itself is shown or edited; elsewhere a recent read is reused.
profile_is_shown=st.session_state.get("editing") or st.session_state.get("main_page","Play")=="Profile" or st.session_state.pop("profile_changed",False)
try: profile=profile_cache.get(auth.user.id,repo.load,time.time(),fresh=bool(profile_is_shown))
except Exception:
    st.error("We couldn’t load your profile. Please retry; your saved information hasn’t changed.")
    if st.button("Retry"):st.rerun()
    st.stop()
picture=None
if profile:
    try:
        if profile.get("image_mode")=="Avatar":
            picture=page_speed.rendered_avatar(tuple(sorted((profile.get("avatar") or DEFAULT_AVATAR).items())))
        else:
            # A photo is downloaded once per session and again only when its path changes.
            photos=st.session_state.setdefault("own_photo",{})
            path=profile.get("image_path")
            if path not in photos:
                photos.clear();photos[path]=repo.image(path)
            picture=photos[path]
    except Exception:pass
brand,profile_slot,friends_slot,chats_slot=st.columns([3.35,1.2,1.2,1.2],vertical_alignment="center")
with brand:
    # The logo and wordmark are one button that opens Play; assets/navigation.css gives it the brand look.
    st.html('<style>.st-key-open_home button::before{background-image:url("data:image/png;base64,'+logo_small+'")}</style>')
    if st.button('Uni**Arena**',key='open_home') and profile:
        navigate('Play')
with profile_slot:
    st.html('<style>'+profile_button_avatar_css(page_speed.thumbnail(picture or page_speed.rendered_avatar(tuple(sorted(DEFAULT_AVATAR.items()))),84))+'</style>')
    if st.button('Profile',use_container_width=True,key='open_profile'):
        navigate('Profile')
with friends_slot:
    if profile and st.button('Friends',use_container_width=True,key='open_friends'):
        navigate('Friends')
with chats_slot:
    if profile:chat_dropdown(auth.client)
if profile and st.session_state.get('chat_open'):
    private_chat_dialog(auth.client,st.session_state.chat_open,picture)
if profile:
    tabs=['Decks','Play','Leaderboard','Study Plan']
    columns=st.columns(len(tabs))
    page=st.session_state.get('main_page','Play')
    if str(st.query_params.get('state','')).startswith('sdplan.'):page=st.session_state.main_page='Study Plan'
    for col,label in zip(columns,tabs):
        if col.button(label,key='nav_'+label,type='primary' if page==label else 'secondary',use_container_width=True):
            navigate(label)
    if st.session_state.get('play_exit_to'):
        st.warning('Leave this round? This counts as a loss and your opponent wins. Your question timer continues while you decide.')
        yes,no=st.columns(2)
        if no.button('Stay in round'):
            st.session_state.pop('play_exit_to',None);st.rerun()
        if yes.button('Confirm abandonment'):
            from db import PlayRepository
            result=play_request(PlayRepository(auth.client),'abandon',{'duel_id':st.session_state.get('play_duel'),'confirmed':True})
            if result is not None:
                st.session_state.main_page=st.session_state.pop('play_exit_to')
                st.session_state.play_in_round=False
                st.session_state.pop('play_duel',None);st.session_state.pop('play_feedback',None);st.rerun()
        st.stop()
    if page=='Play':
        play_screen(auth.client,profile);st.stop()
    if page=='Decks':
        decks_screen(auth.client,profile);st.stop()
    if page=='Friends':
        st.title('Friends')
        friends=FriendsRepository(auth.client)
        try:friend_state=friends.action('list')
        except ValueError as exc:
            st.error(str(exc))
            if st.button('Retry friends'):st.rerun()
        else:friends_screen(friends,repo,friend_state)
        st.stop()
    if page=='Study Plan':
        study_plan_screen(auth.client,profile,auth.user.id);st.stop()
    if page=='Leaderboard':
        leaderboard_screen(auth.client,repo,profile);st.stop()
    if page in ('Leaderboard','Study Plan'):
        st.title(page)
        descriptions={'Play':'Challenge friends to quiz duels using your course decks.','Leaderboard':'See how your study progress compares with other students.','Study Plan':'Organize your study sessions and upcoming goals.'}
        st.write(descriptions[page]);st.info('Coming soon')
        st.stop()
editing=not profile or st.session_state.get("editing",False)
if not editing:
    friends=FriendsRepository(auth.client)
    try:friend_state=friends.action("list")
    except ValueError as exc:
        friend_state=None
        st.warning(str(exc))
    left,right=st.columns([1,3])
    with left:portrait(picture or render_avatar(DEFAULT_AVATAR),176)
    with right:
        code_label=("#"+friend_state["code"]) if friend_state else ""
        st.html(f'<h1 style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin:0 0 16px;color:var(--sd-text)"><span>{escape(profile["username"])}</span><span aria-label="Your friend code" style="font-size:16px;font-weight:400;letter-spacing:.03em;color:var(--sd-muted)">{escape(code_label)}</span></h1>')
        st.html(fresh_module("profile_summary").profile_stats_html(xp_breakdown(profile),profile.get("win_streak",0),len(friend_state["friends"]) if friend_state else None))
        st.write(profile["university"])
        degree_labels={"Bachelor's":"Bachelor","Master's":"Master","Doctorate":"Doctorate","Associate":"Associate degree","Diploma / certificate":"Diploma / certificate"}
        degree=degree_labels.get(profile.get("degree"),"")
        field=profile.get("area","")
        study=degree+(" in "+field if degree and field else field)
        if profile.get("graduation_year"):
            study+=(" · " if study else "")+f"Class of {profile['graduation_year']}"
        if study:st.write(study)
        st.caption(" · ".join(profile["languages"]))
        edit,sign_out=st.columns(2)
        with edit:
            if st.button("Edit profile",use_container_width=True):st.session_state.editing=True;st.rerun()
        with sign_out:
            st.html('<style>.st-key-profile_sign_out button{background:#fff1f2!important;color:#b42318!important;border-color:#fda4af!important}.st-key-profile_sign_out button:hover{background:#ffe4e6!important;border-color:#fb7185!important}</style>')
            if st.button("Sign out",key="profile_sign_out",use_container_width=True):
                message=auth.sign_out().message
                for k in list(st.session_state):del st.session_state[k]
                st.session_state.browser_loaded=True;st.session_state.started=True
                st.session_state.notice=message;st.rerun()
    st.subheader("Your courses")
    st.caption("Only you can see your course selections.")
    for course in profile["courses"]:st.write(":material/school: "+course)
    if st.session_state.get("pending_invite"):
        st.info("You have a friend invitation. Open Friends to review and accept it.")
    if st.session_state.get("adding_courses"):
        # The same course selector as in Edit profile; only the courses change, everything else is saved back as it is.
        from course_catalog import course_options,load_university_courses,match_courses
        if st.session_state.get("shared_courses_for")!=profile["university"]:
            st.session_state.shared_courses=load_university_courses(auth.client,profile["university"])
            st.session_state.shared_courses_for=profile["university"]
        listed_courses=[*CATALOG.get(profile["university"],[]),*st.session_state.get("shared_courses",[])]
        own_courses=match_courses(profile["courses"],listed_courses)
        chosen_courses=st.multiselect("Your courses",course_options(listed_courses,own_courses),default=own_courses,accept_new_options=True,placeholder="Choose courses or type a new one",key="profile_course_editor")
        chosen_courses=match_courses(chosen_courses,listed_courses)
        st.caption("The list shows courses that students at your university have already added. If yours is missing, type it and press Enter; it then appears for your classmates too.")
        save_courses,cancel_courses=st.columns(2)
        if save_courses.button("Save courses",type="primary",use_container_width=True):
            try:
                repo.save(dict(username=profile["username"],university=profile["university"],courses=chosen_courses,languages=profile["languages"],avatar=profile.get("avatar") or DEFAULT_AVATAR,
                               degree=profile.get("degree","Not specified"),area=profile.get("area",""),graduation_year=profile.get("graduation_year")),
                          profile.get("image_mode","Avatar"),None,profile.get("image_path"))
                st.session_state.adding_courses=False;st.session_state.pop("profile_course_editor",None);st.session_state.pop("shared_courses_for",None)
                st.session_state.profile_changed=True;st.session_state.notice="Your courses are saved.";st.rerun()
            except ValueError as exc:st.error(str(exc))
        if cancel_courses.button("Cancel",use_container_width=True):
            st.session_state.adding_courses=False;st.session_state.pop("profile_course_editor",None);st.rerun()
    elif st.button("Add courses",icon=":material/add:"):
        st.session_state.adding_courses=True;st.rerun()
    st.caption("Your username, university, languages, chosen image, XP and streak are visible to signed-in students. Your email and courses are private.")
    st.stop()

st.title("Make yourself at home." if not profile else "Edit your profile")
st.write("Tell us what you’re studying and choose how you’ll appear to other students.")
profile=profile or {}
metadata=getattr(auth.user,"user_metadata",{}) or {}
name=st.text_input("Username",value=profile.get("username",metadata.get("username","")),key="profile_username")
st.caption("3–24 letters, numbers or underscores. No spaces. Your username is visible to other students.")
profile_username_error=st.empty()
if "chosen_university" not in st.session_state:
    saved_university=st.session_state.get("university_selection") or profile.get("university","")
    st.session_state.chosen_university="" if "prototype catalog" in saved_university else saved_university
university=st.session_state.chosen_university
# Type-ahead field: suggestions from universities already in use and, live, from the ROR directory.
if "known_universities" not in st.session_state:
    st.session_state.known_universities=load_universities(auth.client)
known_universities=st.session_state.known_universities
picked,picked_from=fresh_module("university_picker").university_picker(known_universities,university,key="university_picker_"+str(st.session_state.get("university_pick",0)))
if picked!=university:
    st.session_state.chosen_university=university=picked
    st.session_state.university_results=[];st.session_state.university_search_error=None;st.session_state.university_lookup=None
    # A name picked from the suggestions is final; one that was only typed is also looked up on the server.
    if picked and picked_from=="typed" and picked.lower() not in {name.lower() for name in known_universities}:
        st.session_state.university_lookup=picked
        try:
            with st.spinner("Looking up universities…"):
                st.session_state.university_results=search_universities(picked)
        except (ValueError,UniversitySearchError) as exc:
            st.session_state.university_search_error=str(exc)
    st.rerun()  # redraw so the selector lists the new choice and the course list follows the university
if university and st.session_state.get("university_lookup")==university:
    results=st.session_state.get("university_results",[])
    if st.session_state.get("university_search_error"):
        st.warning(st.session_state.university_search_error)
    elif results:
        st.caption(f"Official names matching “{university}”. Choose one, or keep what you typed.")
    else:
        st.info("No match found in the directory. Your university is kept as you typed it.")
    for record in results:
        if st.button(record["label"],key="uni_"+record["id"],use_container_width=True):
            st.session_state.chosen_university=record["label"]
            st.session_state.university_results=[];st.session_state.university_lookup=None
            st.session_state.university_pick=st.session_state.get("university_pick",0)+1
            st.rerun()
degree=st.selectbox("Degree level (optional)",DEGREES,index=DEGREES.index(profile.get("degree","Not specified")))
saved_area=" ".join(str(profile.get("area") or "").split())
area_options=field_options(saved_area)
area=st.selectbox("Field of study (optional)",area_options,index=area_options.index(saved_area) if saved_area else None,placeholder="Search the list or type your own",accept_new_options=True,help="Common degree subjects. Type your field if it is not listed.")
area=" ".join(str(area or "").split())[:120]
graduation_year=st.number_input("Expected graduation year (optional)",min_value=2000,max_value=2100,value=profile.get("graduation_year"),step=1,placeholder="For example: 2028",help="Your planned graduation year. Private and editable later.")
st.caption("Degree level and field of study are private for now, ready for future matching.")
if st.session_state.get("shared_courses_for")!=university:
    st.session_state.shared_courses=load_university_courses(auth.client,university)
    st.session_state.shared_courses_for=university
shared_courses=st.session_state.get("shared_courses",[])
listed_courses=[*CATALOG.get(university,[]),*shared_courses]
own_courses=match_courses(profile.get("courses",[]),listed_courses)
courses=st.multiselect("Your courses",course_options(listed_courses,own_courses),default=own_courses,accept_new_options=True,placeholder="Choose courses or type a new one")
courses=match_courses(courses,listed_courses)
st.caption("The list shows courses that students at your university have already added. If yours is missing, type it and press Enter; it then appears for your classmates too. If you change university, review your courses before saving.")
languages=st.multiselect("Languages",LANGUAGES,default=profile.get("languages",[]))
st.caption("University and languages are visible to signed-in students. Which courses you take stays private; only the course names in use at a university are shared.")
st.subheader("Your look")
mode=st.radio("Profile image",["Avatar","Photo"],horizontal=True,index=1 if profile.get("image_mode")=="Photo" else 0)
avatar=dict(st.session_state.get("avatar_draft") or profile.get("avatar") or DEFAULT_AVATAR)
image=None;image_valid=True
if mode=="Avatar":
    avatar=avatar_picker(avatar,key="avatar_carousel")
    st.session_state.avatar_draft=dict(avatar)
    image=render_avatar(avatar)
    st.caption("Choose Skin, Hair, Hair color, Clothes or Accessories. Swipe left/right on the character to try the next design. Changes are kept in your draft until you save.")

else:
    upload=st.file_uploader("Upload a photo",type=["jpg","jpeg","png"])
    st.caption("JPEG or PNG, up to 5 MB. Only your cropped image will be saved.")
    if upload:
        x=st.slider("Crop horizontal position",0.,1.,.5,.05)
        y=st.slider("Crop vertical position",0.,1.,.5,.05)
        zoom=st.slider("Crop zoom",1.,3.,1.,.1)
        try:
            image=crop_photo(upload.getvalue(),x,y,zoom)
            st.image(image,width=200,caption="Your saved crop")
        except ValueError as exc:st.error(str(exc));image_valid=False
    elif profile.get("image_mode")=="Photo":
        try:st.image(repo.image(profile["image_path"]),width=160)
        except Exception:st.warning("Your current photo preview is unavailable.")
    else:
        st.info("Choose a photo, or switch to Avatar to use the default.")
        image_valid=False
if st.button("Save profile",type="primary",disabled=not image_valid,use_container_width=True):
    try:
        repo.save(dict(username=name,university=university,courses=courses,languages=languages,avatar=avatar,degree=degree,area=area,graduation_year=graduation_year),
                  mode,image,profile.get("image_path"))
        st.session_state.editing=False
        st.session_state.profile_changed=True;st.session_state.notice="Your profile is saved."
        st.rerun()
    except ValueError as exc:
        if "username" in str(exc).lower():
            profile_username_error.error(str(exc))
            st.markdown("<style>.st-key-profile_username input{border:2px solid #D84550!important}</style>",unsafe_allow_html=True)
        else:st.error(str(exc))
if profile and st.button("Cancel changes"):
    st.session_state.editing=False
    st.rerun()
