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
from recovery import recovery_callback, store_recovery_proof
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
from ui_icons import inline_icon
from answer_order import display_options
from round_effects import accuracy_chip, combo_markup, INTRO_SECONDS, countdown_overlay, streak_badge, streak_length, streak_milestone
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
st.html('<style>'+(Path(__file__).parent/'assets'/'navigation.css').read_text()+(Path(__file__).parent/'assets'/'confirm-modal.css').read_text()+'</style>')
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
        select_chat(result['id'])


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


def select_chat(thread_id):
    st.session_state.chat_open = thread_id
    st.session_state.pop('chat_choosing_friend', None)
    navigate('Chats')


@st.fragment(run_every='15s')
def chat_navigation(client, active):
    # The inbox owns the unread count while the Chats page is open.
    unread = 0
    if not active:
        data = chat_call(client, 'list', quiet=True)
        if data is not None:
            unread = sum(thread['unread'] for thread in data['threads'])
    label = f'Chats ({unread})' if unread else 'Chats'
    if st.button(label, key='open_chats', type='primary' if active else 'secondary', width='stretch'):
        navigate('Chats')


def chat_avatar_url(picture):
    default = page_speed.rendered_avatar(tuple(sorted(DEFAULT_AVATAR.items()))) if not picture else picture
    thumbnail = page_speed.thumbnail(default, 84)
    return 'data:image/png;base64,' + base64.b64encode(thumbnail).decode()


def chat_person_avatar(image_repo, person):
    path = person.get('image_path')
    if path:
        photos = st.session_state.setdefault('chat_portraits', {})
        if path in photos:
            return photos[path]
        try:
            picture = image_repo.image(path)
        except Exception:
            picture = None
        if picture:
            if len(photos) >= 64:
                photos.pop(next(iter(photos)))
            photos[path] = chat_avatar_url(picture)
            return photos[path]
    return chat_avatar_url(None)


def chat_list_item(image_repo, person, label, key, *, preview='', unread=0, selected=False):
    username = escape(person['username'])
    avatar = chat_person_avatar(image_repo, person)
    row_class = 'sd-chat-row is-selected' if selected else 'sd-chat-row'
    preview_html = f'<span class="sd-chat-preview">{escape(preview)}</span>' if preview else ''
    unread_html = f'<span class="sd-chat-unread" aria-label="{unread} unread">{unread}</span>' if unread else ''
    with st.container(key='chat_list_item_' + key):
        st.html(
            f'<div class="{row_class}"><img src="{avatar}" alt="">'
            f'<span class="sd-chat-row-text"><strong>{username}</strong>{preview_html}</span>'
            f'{unread_html}</div>'
        )
        return st.button(label, key=key, width='stretch')


def start_chat_with_friend(client, threads):
    try:
        relationships = FriendsRepository(client).action('list')
    except ValueError as exc:
        st.error(str(exc))
        return
    friends = [entry['person'] for entry in relationships.get('friends', [])]
    if not friends:
        st.caption('Add friends on the Friends page to start a conversation.')
        return

    existing_peers = {thread.get('user_id') for thread in threads}
    candidates = sorted(
        (person for person in friends if person['id'] not in existing_peers),
        key=lambda person: person['username'].casefold(),
    )
    if not candidates:
        st.caption('You already have a conversation with each of your friends.')
        return

    image_repo = ProfileRepository(client, st.session_state.auth.user.id)
    with st.container(height=390, border=False, key='chat_friend_list'):
        for person in candidates:
            if chat_list_item(image_repo, person, 'Chat with ' + person['username'], 'chat_start_friend_' + person['id']):
                open_private_chat(client, person['id'])


@st.fragment(run_every='15s')
def chat_inbox(client):
    data = chat_call(client, 'list', quiet=True)
    choosing = st.session_state.get('chat_choosing_friend', False)
    if choosing:
        st.subheader('Choose a friend')
        if st.button('Back to conversations', key='chat_cancel_start', icon=':material/arrow_back:', width='stretch'):
            st.session_state.pop('chat_choosing_friend', None)
            st.rerun()
    else:
        st.subheader('Conversations')
        if st.button('Start conversation', key='chat_start', icon=':material/add_comment:', type='primary',
                     width='stretch', disabled=data is None):
            st.session_state.chat_choosing_friend = True
            st.rerun()

    if data is None:
        st.error('Could not load conversations. Try again.')
        if st.button('Retry', key='chat_retry_inbox'):
            st.rerun()
        return

    threads = data['threads']
    if choosing:
        start_chat_with_friend(client, threads)
        return
    if not threads:
        st.caption('No conversations yet.')
        return

    image_repo = ProfileRepository(client, st.session_state.auth.user.id)
    active = st.session_state.get('chat_open')
    with st.container(height=390, border=False, key='chat_list'):
        for thread in threads:
            prefix = 'You: ' if thread.get('from_me') else ''
            unread = thread['unread']
            username = thread['username']
            label = 'Open chat with ' + username
            if unread:
                label += f' ({unread} unread)'
            if chat_list_item(
                image_repo, thread, label, 'chat_open_' + thread['id'],
                preview=prefix + thread['preview'], unread=unread, selected=thread['id'] == active,
            ):
                select_chat(thread['id'])


def chats_screen(client, own_picture):
    st.html('<style>' + (Path(__file__).parent / 'assets' / 'chat.css').read_text() + '</style>')
    with st.container(key='chat_workspace'):
        st.title('Chats')
        inbox = st.container(border=True, key='chat_inbox')
        conversation = st.container(border=True, key='chat_detail')

        # Read the active thread before rendering unread badges in the inbox.
        with conversation:
            thread_id = st.session_state.get('chat_open')
            if thread_id:
                if st.button('Back to inbox', key='chat_back_to_inbox', icon=':material/arrow_back:'):
                    st.session_state.pop('chat_open', None)
                    st.session_state.pop('chat_choosing_friend', None)
                    st.rerun()
                chat_conversation(client, thread_id, own_picture)
            else:
                st.html('<div class="sd-chat-empty"><h2>Choose a conversation</h2>'
                        '<p>Select a chat from the list or start one with a friend.</p></div>')
        with inbox:
            chat_inbox(client)


@st.fragment(run_every='3s')
def chat_conversation(client,thread_id,own_picture=None):
    from uuid import uuid4
    data=chat_call(client,'read',{'id':thread_id})
    if data is None:return
    image_repo=ProfileRepository(client,st.session_state.auth.user.id)
    partner_avatar = chat_person_avatar(image_repo, data['partner'])
    identity,friend_controls=st.columns([3,2],vertical_alignment='center')
    with identity:
        username = escape(data['partner']['username'])
        st.html(f'<div class="sd-chat-heading"><img src="{partner_avatar}" alt=""><h2>{username}</h2></div>')
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
    own_avatar = chat_avatar_url(own_picture)
    history_key='chat_history_'+thread_id
    history={m['id']:m for m in st.session_state.get(history_key,[])}
    history.update({m['id']:m for m in data['messages']})
    messages=sorted(history.values(),key=lambda m:m['id'])
    st.session_state[history_key]=messages
    older_key='chat_older_'+thread_id
    if older_key not in st.session_state:st.session_state[older_key]=data['has_older']
    with st.container(height=340, border=True, autoscroll=True, key='chat_messages'):
        if st.session_state[older_key] and messages and st.button('Load earlier messages', key='chat_earlier_' + thread_id):
            older = chat_call(client, 'read', {'id': thread_id, 'before': messages[0]['id']})
            if older is not None:
                history.update({message['id']: message for message in older['messages']})
                st.session_state[history_key] = sorted(history.values(), key=lambda message: message['id'])
                st.session_state[older_key] = older['has_older']
                st.rerun()
        if not messages:st.caption('Start the conversation. Only you and this person can read it.')
        for message in messages:
            with st.chat_message('You' if message['from_me'] else data['partner']['username'],avatar=own_avatar if message['from_me'] else partner_avatar):
                st.text(message['body']);st.caption(('You' if message['from_me'] else data['partner']['username'])+' · '+message['created_at'][:16].replace('T',' ')+' UTC')
    if data['messages']:
        latest=data['messages'][-1]['id'];seen_key='chat_seen_'+thread_id
        if st.session_state.get(seen_key)!=latest and chat_call(client,'seen',{'id':thread_id,'through':latest},quiet=True) is not None:st.session_state[seen_key]=latest
    text_key='chat_text_'+thread_id
    if st.session_state.pop('chat_clear_'+thread_id,False):st.session_state[text_key]=''
    with st.form('chat_send_' + thread_id):
        message_input, send_control = st.columns([4, 1.35], gap='small', vertical_alignment='bottom')
        with message_input:
            text = st.text_area('Message', key=text_key, max_chars=2000, height=72,
                                placeholder='Write a message…', label_visibility='collapsed')
        with send_control:
            send = st.form_submit_button('Send message', icon=':material/send:', type='primary')
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
    """Render an accepted friend with the social actions that are already authorized."""
    person=item["person"]
    avatar,profile,actions=st.columns([.65,1.65,3.85],vertical_alignment="center")
    with avatar:
        try: data=repo.image(person.get("image_path"))
        except Exception:data=None
        portrait(data or render_avatar(DEFAULT_AVATAR),48)
    with profile:
        st.markdown("**"+person["username"]+"**")
        st.caption("Friend")
    with actions:
        battle,study,chat,remove=st.columns([1.35,1.2,.7,.7],gap='small',vertical_alignment='center')
        with battle:
            if st.button('Battle',key='friend_battle_'+item['id'],icon=':material/swords:',use_container_width=True,type='primary'):
                open_friend_match(person,'battle')
        with study:
            if st.button('Study',key='friend_study_'+item['id'],icon=':material/menu_book:',use_container_width=True):
                open_friend_match(person,'study')
        with chat:
            if st.button('Chat',key="friend_chat_"+item["id"],icon=":material/chat:",help="Open chat with "+person["username"],use_container_width=True):
                open_private_chat(friends.client,person["id"])
        with remove:
            if st.button('Remove',key='remove_friend_'+item['id'],use_container_width=True,icon=':material/person_remove:',help='Remove '+person['username']+' as a friend'):
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
    st.html('<style>'+ (Path(__file__).parent/'assets'/'friends.css').read_text()+'</style>')
    if st.session_state.get('study_return_after_friends'):
        if st.button('Back to Study Together',icon=':material/arrow_back:'):
            st.session_state.pop('study_return_after_friends',None)
            st.session_state.main_page='Play';st.session_state.study_active=True;st.session_state.study_choice='Study together';st.rerun()

    friend_count=len(state['friends'])
    st.title('Friends')

    token=st.session_state.get("pending_invite")
    if token:
        with st.container(border=True,key='friends_link_invitation'):
            st.subheader('Friend invitation')
            try:
                invitation_token(token)
                preview=friends.action('preview_invite',token)
                public_person(preview['person'],repo)
                st.write('Accept this invitation to add each other as friends.')
                if st.button('Accept invitation',type='primary'):
                    if friend_action(friends,'accept_invite',token):
                        st.session_state.pop('pending_invite',None)
                        if 'invite' in st.query_params:del st.query_params['invite']
                        st.rerun()
            except ValueError as exc:st.warning(str(exc))
            if st.button('Dismiss invitation'):
                st.session_state.pop("friend_preview",None)
                st.session_state.pop('pending_invite',None)
                if 'invite' in st.query_params:del st.query_params['invite']
                st.rerun()

    main,invite=st.columns([2.05,1],gap='large')
    with main:
        if state['incoming']:
            for item in state['incoming']:
                with st.container(border=True,key='friends_incoming_'+item['id']):
                    person=item['person']
                    avatar,identity,accept,decline=st.columns([.65,2.5,.9,.95],vertical_alignment='center')
                    with avatar:
                        try:data=repo.image(person.get('image_path'))
                        except Exception:data=None
                        portrait(data or render_avatar(DEFAULT_AVATAR),48)
                    with identity:
                        st.markdown('**'+person['username']+' wants to be your friend**')
                    with accept:
                        if st.button('Accept',key='accept_'+item['id'],type='primary',use_container_width=True):
                            if friend_action(friends,'accept',item['id']):st.rerun()
                    with decline:
                        if st.button('Decline',key='decline_'+item['id'],use_container_width=True):
                            if friend_action(friends,'decline',item['id']):st.rerun()

        friends_heading,friends_search=st.columns([1.2,1],vertical_alignment='center')
        with friends_heading:
            st.html(f'<div class="friends-heading-inline" aria-label="{friend_count} friends"><span>Your friends</span><strong>{friend_count}</strong></div>')
        with friends_search:
            query=st.text_input('Search friends',placeholder='Search friends',key='friends_local_search',label_visibility='collapsed')
        visible_friends=[item for item in state['friends'] if not query or query.casefold() in item['person']['username'].casefold()]
        if not visible_friends:
            st.caption('No friends match your search.' if query else 'Nothing here yet.')
        else:
            with st.container(border=True,key='friends_list'):
                for item in visible_friends:
                    friend_match_row(item,repo,friends)

        st.subheader('Find students at your university')
        try:university_directory=friends.university_profiles()
        except ValueError as exc:st.error(str(exc));university_directory={'profiles':[]}
        students=university_directory['profiles']
        if students:
            st.caption(f"Students with a profile at {university_directory['university']}.")
            with st.container(border=True,key='friends_university_directory'):
                for student in students:
                    avatar,name,university,action=st.columns([.6,2.4,2.8,1.2],vertical_alignment='center')
                    with avatar:
                        try:data=repo.image(student.get('image_path'))
                        except Exception:data=None
                        portrait(data or render_avatar(DEFAULT_AVATAR),44)
                    with name:st.markdown('**'+student['username']+'**')
                    with university:st.caption(university_directory['university'])
                    with action:
                        if st.button('Add',key='university_friend_'+student['id'],icon=':material/person_add:',use_container_width=True):
                            try:
                                result=friends.request_university_friend(student['id'])
                                st.session_state.notice=result.get('message','Friend request sent.');st.rerun()
                            except ValueError as exc:st.error(str(exc))
        else:st.caption('No other students from your university are available to add right now.')

    with invite:
        with st.container(border=True,key='friends_invite_card'):
            st.html('<h2 class="friends-card-title">Invite friends</h2>')
            st.html('<p class="friends-invite-intro">Share your code or a link — you decide who to invite.</p>')
            st.html('<p class="friends-invite-label">YOUR FRIEND CODE</p>')
            st.code('#'+state['code'],language=None)
            st.divider()
            st.html('<p class="friends-invite-label">ADD FRIEND BY CODE</p>')
            code_entry,find_action=st.columns([3.2,1],vertical_alignment='center')
            with code_entry:
                friend_code=st.text_input('Friend code',placeholder='#AB23CD45',max_chars=12,key='friends_code_entry',label_visibility='collapsed')
            with find_action:
                find=st.button('Add',key='friends_find_code',use_container_width=True,type='primary',icon=':material/person_add:')
            if find:
                st.session_state.pop('friend_preview',None)
                try:
                    normalized=normalize_friend_code(friend_code)
                    result=friends.lookup(normalized)
                    st.session_state.friend_preview={'code':normalized,'person':result['person']}
                except ValueError as exc:st.error(str(exc))
            if preview:=st.session_state.get('friend_preview'):
                with st.container(border=True,key='friends_code_preview'):
                    person=preview['person']
                    avatar,identity=st.columns([.55,2.4],vertical_alignment='center')
                    with avatar:
                        try:data=repo.image(person.get('image_path'))
                        except Exception:data=None
                        portrait(data or render_avatar(DEFAULT_AVATAR),44)
                    with identity:st.markdown('**'+person['username']+'**')
                    profile_action,add_action=st.columns(2)
                    with profile_action:
                        with st.popover('View profile',icon=':material/person:',use_container_width=True):
                            public_person(person,repo)
                    with add_action:
                        if st.button('Add',key='send_friend_request',type='primary',use_container_width=True):
                            if friend_action(friends,'request',preview['code']):
                                st.session_state.pop('friend_preview',None);st.rerun()
            st.divider()
            active_until=None
            if state.get('invite_expires'):
                from datetime import datetime
                try:
                    expires=datetime.fromisoformat(state['invite_expires'].replace('Z','+00:00'))
                    active_until='Active until '+expires.strftime('%d %b')
                except (TypeError,ValueError):
                    active_until='Invitation link active'
            if link_token:=st.session_state.get('share_invite_token'):
                try:share_invitation(invitation_url(config('PUBLIC_APP_URL') or config('APP_URL') or 'http://localhost:8501',link_token),active_until or 'Invitation link active')
                except ValueError as exc:st.info(str(exc))
            else:
                st.html('<p class="friends-invite-label">INVITATION LINK</p>')
                if active_until:
                    st.html(f'<p class="friends-invite-active"><span></span>{active_until}</p>')
            new_link,revoke_link=st.columns(2)
            with new_link:
                if st.button('New link',key='create_friend_invite',use_container_width=True,icon=':material/refresh:'):
                    result=friend_action(friends,'create_invite')
                    if result:
                        st.session_state.share_invite_token=result['token'];st.rerun()
            with revoke_link:
                if state.get('invite_expires') and st.button('Revoke',key='revoke_friend_invite',use_container_width=True):
                    if friend_action(friends,'revoke_invite'):
                        st.session_state.pop('share_invite_token',None);st.rerun()
            st.divider()
            st.html('<h2 class="friends-card-title">Open invitations</h2>')
            if not state['sent']:st.caption('No pending requests.')
            for item in state['sent']:
                person=item['person']
                sent_name,cancel=st.columns([2,1],vertical_alignment='center')
                with sent_name:st.write(person['username'])
                with cancel:
                    if st.button('Cancel',key='cancel_'+item['id'],use_container_width=True):
                        if friend_action(friends,'cancel',item['id']):st.rerun()

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
        if st.button('Back to Deck studio' if st.session_state.get('deck_studio') else 'Back to Study deck',icon=':material/arrow_back:'):
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
    if st.session_state.get('deck_studio'):
        deck_studio_screen(client,profile);return
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
            st.html('<div class="deck-create-icon">'+inline_icon('add')+'</div>')
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
            st.html('<div class="deck-create-icon">'+inline_icon('file')+'</div>')
            st.markdown('#### AI Anki import')
            st.caption('Import Anki cards, then review AI-generated questions.')
            if st.button('Import Anki deck',use_container_width=True):
                st.session_state.anki_import_open=True;st.session_state.pop('anki_import_result',None);st.rerun()
    with ai:
        with st.container(border=True,key='deck_create_slides'):
            st.html('<div class="deck-create-icon">'+inline_icon('sparkles')+'</div>')
            st.markdown('#### AI from lecture slides')
            st.caption('Upload text-based PDF slides, then review generated questions.')
            if st.button('Generate with AI',use_container_width=True):st.session_state.pdf_import_open=True;st.session_state.pop('pdf_import_result',None);st.rerun()
    with st.container(border=True,key='deck_studio_entry'):
        studio_text,studio_open=st.columns([5,2],vertical_alignment='center')
        with studio_text:
            st.markdown('#### :material/edit: Deck studio')
            st.caption('Edit, publish and track every deck you created: private drafts, published Study decks and Battle decks, with their dates.')
        if studio_open.button('Open Deck studio',key='open_deck_studio',icon=':material/design_services:',type='primary',use_container_width=True):
            st.session_state.deck_studio=True;st.rerun()
    course_names=list(dict.fromkeys(profile['courses']))
    public_study=study_public_request(client,'list')
    if public_study is None:return
    course_keys={course.strip().casefold() for course in course_names}
    study_decks=[deck for deck in public_study.get('decks',[]) if deck.get('course','').strip().casefold() in course_keys]
    study_by_course={course.strip().casefold():[] for course in course_names}
    for deck in study_decks:study_by_course.setdefault(deck.get('course','').strip().casefold(),[]).append(deck)

    def study_deck_rows(decks,index):
        for deck in decks:
            with st.container(key=f'course_list_deck_{index}_{deck["id"]}'):
                info,count,action=st.columns([4,1,1],vertical_alignment='center')
                with info:st.markdown(':material/menu_book: **'+deck['name']+'**')
                with count:st.caption(f'{deck["count"]} questions')
                with action:
                    if st.button('Study',key=f'course_study_{index}_{deck["id"]}',icon=':material/menu_book:',use_container_width=True):
                        open_course_study_deck(client,deck)

    def sorted_study_decks(decks,sort_order):
        if sort_order=='A–Z':return sorted(decks,key=lambda deck:deck['name'].casefold())
        return sorted(decks,key=lambda deck:deck.get('published_at') or '',reverse=True)

    st.subheader('Your courses')
    for index,course in enumerate(course_names):
        course_key=course.strip().casefold()
        course_study_decks=study_by_course.get(course_key,[])
        study_count=len(course_study_decks)
        with st.container(border=True,key='course_list_'+str(index)):
            initials=''.join(part[:1] for part in course.split()[:2]).upper() or 'C'
            status=f'<p>{study_count} Study deck{"s" if study_count!=1 else ""} available</p>' if study_count else ''
            st.html('<div class="course-list-hero"><span class="course-list-initials">'+escape(initials)+'</span><div><h3>'+escape(course)+'</h3>'+status+'</div><b>'+str(study_count)+' Deck'+('s' if study_count!=1 else '')+'</b></div>')
            with st.container(key=f'course_list_search_{index}'):
                query=st.text_input(f'Search {course} Study decks',placeholder=f'Search {course} Study decks',key=f'course_study_search_{index}',label_visibility='collapsed').strip().casefold()
            visible_study_decks=[deck for deck in course_study_decks if not query or query in deck.get('name','').casefold()]
            if query:
                with st.container(border=True,key=f'course_list_results_{index}'):
                    if not visible_study_decks:st.caption(f'No Study decks in {course} match your search.')
                    else:study_deck_rows(visible_study_decks,index)
            else:
                with st.expander('View all study decks'):
                    if not course_study_decks:st.caption(f'No Study decks in {course} yet.')
                    else:
                        with st.container(key=f'course_list_sort_{index}'):
                            sort_order=st.radio('Sort Study decks',['Recently added','A–Z'],key=f'course_study_sort_{index}',horizontal=True,label_visibility='collapsed')
                        study_deck_rows(sorted_study_decks(course_study_decks,sort_order),index)

def deck_studio_timezone():
    from zoneinfo import ZoneInfo
    name=getattr(st.context,'timezone',None) or 'Europe/Berlin'
    try:ZoneInfo(name)
    except Exception:name='Europe/Berlin'
    return name


def deck_studio_edit(client,deck_id):
    from copy import deepcopy
    deck=study_request(client,'deck',{'id':deck_id,'shared':False})
    if deck is None:return
    st.session_state.study_draft={key:deepcopy(deck[key]) for key in ['id','name','course','language','cards']}
    st.session_state.study_revision=deck['revision'];st.session_state.pop('study_review',None)
    st.session_state.study_library=True;st.session_state.pop('deck_studio',None);st.rerun()


def deck_studio_screen(client,profile):
    """Own Study and Battle decks with status, times and edit or publish actions."""
    from db import StudyRepository
    from logic import deck_studio_created_text,deck_studio_groups,format_deck_time
    st.header(':material/design_services: Deck studio')
    st.caption('Decks created by you. Edit them, publish them to your university or turn them into Battle decks.')
    if st.button('Back to Decks',icon=':material/arrow_back:'):
        st.session_state.pop('deck_studio',None);st.rerun()
    try:decks=StudyRepository(client).studio()
    except ValueError as exc:st.error(str(exc));return
    zone=deck_studio_timezone();groups=deck_studio_groups(decks)
    choice=st.segmented_control('Deck studio filter',list(groups),default='All',key='deck_studio_filter',label_visibility='collapsed') or 'All'
    if not groups[choice]:
        st.info('You have not created any decks yet. Create one on the Decks page.' if choice=='All' else 'No decks match this filter.')
    for deck in groups[choice]:
        did=deck['id'];study=deck['kind']=='study'
        with st.container(border=True,key=f"studio_deck_{deck['kind']}_{did}"):
            info,status,times,actions=st.columns([2,1.1,1.9,2.5],vertical_alignment='center')
            info.markdown((':material/menu_book:' if study else ':material/swords:')+' **'+deck['name']+'**')
            info.caption(f"{deck['course']} · {deck['language']} · {deck['count']} questions")
            created=deck_studio_created_text(deck,zone)
            times.caption('Created '+(created[0].lower()+created[1:] if created.startswith('On or before') else created))
            if not study:
                status.markdown(':red-badge[Battle · public]');times.caption('Fixed 15-question snapshot')
                continue
            times.caption('Last edited '+format_deck_time(deck['updated_at'],zone))
            if deck.get('published_at'):
                status.markdown(':green-badge[Published]');status.caption('Published since '+format_deck_time(deck['published_at'],zone))
            else:
                status.markdown(':orange-badge[Private]');status.caption('Only you can see it')
            edit,publish,battle=actions.columns([.8,1.3,1.35])
            if edit.button('Edit',key='studio_edit_'+did,use_container_width=True):deck_studio_edit(client,did)
            if deck.get('published_at'):
                if publish.button('Unpublish',key='studio_unpublish_'+did,use_container_width=True):
                    if study_public_request(client,'unpublish',{'id':did}) is not None:
                        st.session_state.notice='The Study deck is private again.';st.rerun()
            elif publish.button('Publish',key='studio_publish_'+did,type='primary',use_container_width=True):
                if study_public_request(client,'publish',{'id':did}) is not None:
                    st.session_state.notice='Published to students at your university.';st.rerun()
            if battle.button('Battle',key='studio_battle_'+did,icon=':material/swords:',use_container_width=True,disabled=deck['count']<15,help=None if deck['count']>=15 else 'Battle decks need at least 15 questions.'):
                st.session_state.battle_deck_creator=True;st.session_state.battle_source_id=did;st.session_state.battle_return_study=True;st.rerun()


def course_deck_meta(kind,deck):
    if kind=='study':return f"{deck['course']} · {deck['language']} · By {deck['author']} · {deck['count']} questions"
    return f"{deck['course']} · {deck['language']} · By {deck.get('author','Student')} · {deck.get('count',15)} questions"


def open_course_study_deck(client,deck):
    """Open Study Mode with the selected published Study deck preselected."""
    deck_id=deck['id']
    if not deck.get('owned'):
        copied=study_public_request(client,'copy',{'id':deck_id})
        if copied is None:return
        deck_id=copied['id']
    st.session_state.main_page='Play'
    st.session_state.study_active=True
    st.session_state.study_choice='Study alone'
    st.session_state.study_deck_preselection=deck_id
    st.session_state.pop('study_session',None)
    st.session_state.pop('study_join',None)
    st.rerun()


def anki_import_reset():
    for key in [key for key in st.session_state if str(key).startswith(('anki_import_result','anki_image_'))]:st.session_state.pop(key,None)


def anki_read_image_cards(repository,image_cards):
    """Read the text on every image card once and keep it in the session for review."""
    from logic import combine_card_text
    results=[];bar=st.progress(0.0,text='Reading text from images…')
    for index,card in enumerate(image_cards):
        images=[{**image,'id':f'{index}-{number}'} for number,image in enumerate(card['images'])]
        try:texts=repository.read_image_text(images);error=''
        except ValueError as exc:texts={};error=str(exc)
        sides={side:combine_card_text(card[side],[texts.get(image['id'],'') for image in images if image['side']==side]) for side in ('front','back')}
        results.append({**sides,'error':error})
        st.session_state[f'anki_image_front_{index}']=sides['front'];st.session_state[f'anki_image_back_{index}']=sides['back']
        bar.progress((index+1)/len(image_cards),text=f'Read {index+1} of {len(image_cards)} image cards')
    bar.empty();st.session_state.anki_image_text=results


def leave_creation_control(label,key,has_unsaved,message,leave):
    """A Back control that warns in a centred modal before unsaved creation content is dropped."""
    if st.button(label,key=key):
        if has_unsaved:st.session_state.leave_creation_prompt=key;st.rerun()
        else:leave()
    if st.session_state.get('leave_creation_prompt')==key:
        st.html('<div class="round-modal-backdrop"></div>')
        with st.container(key=f'round_leave_modal_{key}'):
            st.html('<p class="round-modal-title">Leave without saving?</p><p class="round-modal-text">'+message+'</p>')
            stay,leave_column=st.columns(2)
            if stay.button('Keep working',key=f'round_leave_stay_{key}',use_container_width=True):
                st.session_state.pop('leave_creation_prompt',None);st.rerun()
            if leave_column.button('Leave and discard',key=f'round_leave_confirm_{key}',use_container_width=True):
                st.session_state.pop('leave_creation_prompt',None);leave()


def anki_import_screen(client,profile):
    from anki_import import AnkiImportError,parse_basic_apkg
    from db import AnkiImportRepository
    repository=AnkiImportRepository(client)
    st.caption('Decks › Import from Anki')
    st.header('Import Basic Anki cards')
    st.info('Two-field Basic cards are accepted, also with images: the text on the images is read with AI and you review it before importing. Cloze, audio and video cards stay in your Anki file.')
    def leave_anki_import():
        anki_import_reset();st.session_state.pop('anki_import_open',None);st.session_state.pop('anki_import_saved',None);st.rerun()
    leave_creation_control('Back to Decks','anki_import_back',bool(st.session_state.get('anki_import_result')) and not st.session_state.get('anki_import_saved'),'Your checked Anki package, including any text read from images, is not saved yet and will be discarded.',leave_anki_import)
    if saved:=st.session_state.get('anki_import_saved'):
        st.success(f"Saved {saved['count']} private source cards.")
        if st.button('Continue to question generation',type='primary'):
            st.session_state.pop('anki_import_open',None);st.session_state.pop('anki_import_saved',None);st.session_state.anki_generation_open=True;st.rerun()
        return
    upload=st.file_uploader('Anki package (.apkg)',type=['apkg'])
    if upload and st.button('Check Anki package',type='primary'):
        anki_import_reset()
        try:st.session_state.anki_import_result=parse_basic_apkg(upload.getvalue())
        except AnkiImportError as exc:st.error(str(exc))
    result=st.session_state.get('anki_import_result')
    if not result:return
    cards=result['cards'];image_cards=result.get('image_cards',[]);skipped=result['skipped']
    reasons={'cloze':'Cloze cards are not supported yet.','media':'Audio and video cards are not supported.','image':'Image cards were skipped because an image is missing, not PNG, JPEG, GIF or WebP, larger than 4 MB, or one of more than three images on a card.','incomplete':'Cards without content on both sides were skipped.','unsupported':'Only two-field Basic cards are supported.','limit':'Only the first 100 valid Basic cards can be imported.'}
    st.success(f'{len(cards)} Basic text cards are ready to import.')
    for reason,text in reasons.items():
        count=sum(item['reason']==reason for item in skipped)
        if count:st.warning(f'{count}: {text}')
    reviewed=[]
    if image_cards:
        count=len(image_cards)
        st.info(f"{count} card{'s' if count!=1 else ''} contain{'s' if count==1 else ''} images. UniArena can read the text on the images with AI so they become text cards. The images are sent to the AI provider only for reading and are not stored.")
        read=st.session_state.get('anki_image_text')
        if read is None:
            if st.button(f"Read text from {count} image card{'s' if count!=1 else ''}",icon=':material/document_scanner:'):
                anki_read_image_cards(repository,image_cards);st.rerun()
        else:
            failed=[item['error'] for item in read if item['error']]
            if failed:st.error(f"{len(failed)} image card{'s' if len(failed)!=1 else ''} could not be read: {failed[0]}")
            with st.expander(f'Review text read from images ({count})',expanded=True):
                st.caption('Check and correct the text. Cards with an empty side are not imported.')
                for index in range(count):
                    front=st.text_area(f'Image card {index+1} · front',key=f'anki_image_front_{index}',height=80)
                    back=st.text_area(f'Image card {index+1} · back',key=f'anki_image_back_{index}',height=80)
                    if front.strip() and back.strip():reviewed.append({'front':front.strip(),'back':back.strip()})
            empty=count-len(reviewed)
            if empty:st.warning(f"No readable text on {empty} image card{'s' if empty!=1 else ''} yet. Type the text yourself or leave {'them' if empty!=1 else 'it'} out.")
    to_save=(cards+reviewed)[:100]
    if not to_save:
        if not image_cards:st.error('No importable Basic cards were found.')
        return
    name=st.text_input('Import name',placeholder='For example: Corporate Finance Anki notes')
    course=st.selectbox('Course',profile['courses'],key='anki_import_course')
    language=st.selectbox('Deck language',profile['languages'],key='anki_import_language')
    if st.button(f'Save {len(to_save)} source cards',type='primary'):
        from logic import import_save_error
        if problem:=import_save_error(name,course,language):st.error(problem)
        else:
            try: saved=repository.save(name=name.strip(),course=course,language=language,cards=to_save)
            except ValueError as exc:st.error(str(exc))
            else:
                anki_import_reset()
                st.session_state.anki_import_saved=saved;st.rerun()

def pdf_import_screen(client,profile):
    from pdf_import import SlideImportError,parse_pdf_slides
    from db import AnkiImportRepository
    st.caption('Decks › AI from lecture slides')
    st.header('Import PDF lecture slides')
    st.info('PDF slides stay private. Only selectable text is supported; scanned PDFs need OCR before import.')
    def leave_pdf_import():
        st.session_state.pop('pdf_import_open',None);st.session_state.pop('pdf_import_result',None);st.session_state.pop('pdf_import_saved',None);st.rerun()
    leave_creation_control('Back to Decks','pdf_import_back',bool(st.session_state.get('pdf_import_result')) and not st.session_state.get('pdf_import_saved'),'Your extracted slide texts are not saved yet and will be discarded.',leave_pdf_import)
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
        from logic import import_save_error
        if problem:=import_save_error(name,course,language):st.error(problem)
        else:
            try:saved=AnkiImportRepository(client).save_slides(name=name.strip(),course=course,language=language,cards=result['cards'])
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
        st.caption("Generating sends the selected card or slide text to Requesty and its model provider. "
                   "Leave out confidential material and personal information.")
        st.button(f'Generate {len(selected)} question drafts',type='primary',disabled=not selected,on_click=request_ai_generation,args=(imported['id'],selected))
    else:st.caption('All source cards from this import already have a draft or were published.')
    drafts=[draft for draft in imported['drafts'] if draft['status']=='draft']
    if not drafts:return
    st.subheader('2. Review drafts');selected_drafts=[]
    unsaved_drafts = []
    if st.button('Include all in Study Deck',key='ai_include_all_'+imported['id']):
        for draft in drafts:st.session_state['ai_include_'+draft['id']]=True
        st.rerun()
    for number,draft in enumerate(drafts,1):
        include,review=st.columns([.26,.74],vertical_alignment='center')
        included = include.checkbox('Include in Study deck',key='ai_include_'+draft['id'])
        if included:
            selected_drafts.append(draft)
        with review.expander(f"Draft {number}: {draft['question'][:70]}",expanded=number==1):
            question=st.text_area('Question',value=draft['question'],key='ai_question_'+draft['id'])
            options=[st.text_input(f'Answer {index+1}',value=option,key=f'ai_option_{draft["id"]}_{index}') for index,option in enumerate(draft['options'])]
            correct=st.radio('Correct answer',range(4),index=draft['correct_option_index'],format_func=lambda value:f'Answer {value+1}',horizontal=True,key='ai_correct_'+draft['id'])
            if included and (question, options, correct) != (draft['question'], draft['options'], draft['correct_option_index']):
                unsaved_drafts.append(str(number))
            edit,discard=st.columns(2)
            if edit.button('Save edits',key='ai_save_'+draft['id']):
                try:repository.update_draft(draft['id'],question,options,correct)
                except ValueError as exc:st.error(str(exc))
                else:st.success('Draft saved.');st.rerun()
            if discard.button('Discard draft',key='ai_discard_'+draft['id']):
                try:repository.discard_draft(draft['id'])
                except ValueError as exc:st.error(str(exc))
                else:st.rerun()
    st.subheader('3. Publish Study deck')
    st.caption('The review above is the deck review: publishing creates the Study deck directly. You can edit it anytime under Decks.')
    name=st.text_input('Study deck name',value=f"{imported['name']} questions",key='ai_study_name_'+imported['id'])
    if unsaved_drafts:
        st.warning('Choose Save edits for the following drafts before publishing: ' + ', '.join(unsaved_drafts))
    can_publish = bool(selected_drafts) and not unsaved_drafts
    if st.button(f'Publish Study deck from {len(selected_drafts)} drafts',type='primary',disabled=not can_publish) and can_publish:
        from logic import validate_study_deck
        cards=[]
        for draft in selected_drafts:
            answer_ids=[str(uuid4()) for _ in draft['options']]
            cards.append({'id':str(uuid4()),'question':draft['question'],'answers':[{'id':answer_id,'text':option} for answer_id,option in zip(answer_ids,draft['options'])],'correct_answer_id':answer_ids[draft['correct_option_index']],'allow_calculator':False,'chapter':''})
        try:clean=validate_study_deck({'id':str(uuid4()),'name':name,'course':imported['course'],'language':imported['language'],'cards':cards})
        except ValueError as exc:st.error(str(exc))
        else:
            # The server still requires its review handshake; both calls carry the same reviewed snapshot.
            review=study_request(client,'review_deck',{'draft':clean,'revision':0})
            if review is not None:
                saved=study_request(client,'save_deck',{'draft':clean,'revision':0,'review_id':review['id']})
                if saved is not None:
                    try:repository.publish_drafts([draft['id'] for draft in selected_drafts])
                    except ValueError as exc:st.warning(str(exc))
                    st.session_state.pop('anki_generation_open',None)
                    st.session_state.study_library=True;st.session_state.study_deck_open={'id':saved['id']}
                    st.rerun()


def play_request(repository,action,data=None):
    try:return repository.action(action,data)
    except ValueError as exc:st.error(str(exc));return None


def navigate(page):
    if st.session_state.get('play_in_round'):
        st.session_state.play_exit_to=page
    else:
        # A completed/abandoned Google Calendar callback must not keep the user
        # pinned to Study Plan after they choose another navigation destination.
        if page!='Study Plan' and str(st.query_params.get('state','')).startswith('sdplan.'):
            del st.query_params['state']
        if page=='Decks':
            for key in ('study_library','study_deck_open','deck_open','battle_deck_creator','battle_source_id','battle_return_study','deck_studio','anki_import_open','pdf_import_open','anki_generation_open'):
                st.session_state.pop(key,None)
        st.session_state.main_page=page
        if page=='Play':
            st.session_state.pop('study_active',None)
            st.session_state.pop('study_choose',None)
            st.session_state.pop('play_mode_preview',None)
            st.session_state.pop('battle_new_setup',None)
        st.rerun()
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
    def leave_study_editor():
        st.session_state.pop('study_draft');st.session_state.pop('study_review',None);st.rerun()
    leave_creation_control('Leave Study editor','study_editor_leave',True,'Changes that were not saved through a Study review will be discarded. A saved deck keeps its last saved version.',leave_study_editor)


def study_library(client,profile):
    from uuid import uuid4
    from copy import deepcopy
    from logic import new_deck
    st.header('Study decks & progress')
    if st.session_state.get('study_draft'):
        study_editor(client,profile);return
    if st.session_state.get('study_deck_open'):
        choice=st.session_state.study_deck_open
        back,studio=st.columns([1,1])
        if back.button('Back to Study decks',use_container_width=True):st.session_state.pop('study_deck_open');st.rerun()
        if studio.button('Open Deck studio',key='deck_view_open_studio',icon=':material/design_services:',type='primary',use_container_width=True):
            st.session_state.pop('study_deck_open',None);st.session_state.pop('study_library',None)
            st.session_state.deck_studio=True;st.rerun()
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
    show_round_intro('study',sid)
    r=study_request(client,'round',{'id':sid})
    if r is None:return
    from db import StudyRepository
    try:progress=StudyRepository(client).progress(sid)
    except ValueError as exc:st.error(str(exc));return
    st.html('<style>'+ (Path(__file__).parent/'assets'/'study-round.css').read_text()+(Path(__file__).parent/'assets'/'round-effects.css').read_text()+'</style>')
    session_partner_chat(client,'study',sid)
    if st.button('Save and leave Study session'):
        st.session_state.pop('study_session',None);st.rerun()
    state=r['state']
    if state in ('question','feedback'):
        from study_ui import study_progress_tiles
        symbols={'correct':'✓','incorrect':'×','current':'•','open':''}
        current_index=r['index'] if state=='question' else r['index']+1
        streak=streak_length(progress.get('answers',[]))
        flash=r['index'] if state=='feedback' else None
        tiles=study_progress_tiles(progress.get('answers',[]),current_index,r['total'])
        markup=''.join(f'<span class="study-tile study-tile-{tile["state"]}{" round-tile-flash" if flash==tile["number"]-1 else ""}" aria-label="Question {tile["number"]}: {tile["state"]}">{symbols[tile["state"]] or tile["number"]}</span>' for tile in tiles)
        question,overview=st.columns([3,1],gap='large')
        with overview:
            badge=streak_badge(streak)
            foot=('<div class="round-overview-foot">'+badge+'</div>' if badge else '')+combo_markup(streak,pulse=False)
            st.html('<aside class="study-overview"><div class="round-overview-head"><h3>Overview</h3>'+accuracy_chip(progress.get('answers',[]))+'</div><div class="study-overview-grid">'+markup+'</div>'+foot+'</aside>')
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
                burst=''.join(f'<span class="round-confetti c{n}"></span>' for n in range(1,9))
                parts=[]
                for a in display_options(c['answers'],sid,r['index']):
                    text=escape(a['text'])
                    if a['id']==c['correct_answer_id'] and r['correct']:
                        parts.append('<div class="study-answer-card round-burst is-correct is-correct-animated">'+text+burst+'</div>')
                    elif a['id']==c['correct_answer_id']:
                        parts.append('<div class="study-answer-card is-correct is-correct-reveal">'+text+'</div>')
                    elif a['id']==r['answer_id']:
                        parts.append('<div class="study-answer-card is-incorrect">'+text+'</div>')
                    else:
                        parts.append('<div class="study-answer-card is-neutral">'+text+'</div>')
                st.html('<div class="study-answer-grid">'+''.join(parts)+'</div>')
                if not r['correct']:st.html('<div class="round-vignette"></div>')
                elif streak_milestone(streak):st.html('<div class="round-streak-banner">'+streak_milestone(streak)+'</div>')
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
        st.session_state.study_active=True;st.session_state.study_choice='Study alone';st.session_state.main_page='Play'
        open_round('study', started['id'], fresh=True)


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
    css = (Path(__file__).parent / 'assets' / 'study-plan.css').read_text()
    goal_colors = ''.join(
        f'[class*="st-key-study_plan_goal_card_{level}"]{{--goal-color:{STUDY_LEVEL_COLORS[level]}}}'
        for level in ('1', '2', '3')
    )
    st.html(f'<style>{css}{goal_colors}</style>')


def study_plan_add_day_off(key):
    extra=st.session_state.get(key+'extra_day')
    if extra:
        for part in ('dates_options','dates_off'):st.session_state[key+part]=sorted(set(st.session_state.get(key+part,[]))|{extra.isoformat()})


def study_plan_editor(client,profile,decks,user_id=''):
    from datetime import date,time,timedelta
    import study_plan as rules
    draft=st.session_state.plan_draft;today=date.today();key='plan_'+str(draft.get('id','new'))+'_'
    with st.container(horizontal=True,vertical_alignment='center'):
        label='Edit plan' if draft.get('id') else 'New plan'
        st.markdown(f'<p class="study-plan-breadcrumb">Study plan › <strong>{label}</strong></p>',unsafe_allow_html=True)
        actions=st.container(horizontal=True,width='content',vertical_alignment='center')
    configuration,preview=st.columns([1.28,.82],vertical_alignment='top')
    with configuration:
        with st.container(border=True,key='study_plan_editor_courses'):
            st.markdown('<p class="study-plan-step-heading"><span class="study-plan-step-number">1</span>Courses and exams</p>',unsafe_allow_html=True)
            name=st.text_input('Plan name',value=draft['name'],max_chars=60,key=key+'name',placeholder='Plan name, like Winter exams')
            courses=st.multiselect('Courses',profile['courses'],default=[c['course'] for c in draft['courses'] if c['course'] in profile['courses']],key=key+'courses',help='Only courses from your profile can be added.')
            chosen=[];row_widths=[1.1,2.7,1.3]
            if courses:
                for column,label in zip(st.columns(row_widths),['Course','Decks','Exam date']):column.caption(label)
            for course in courses:
                old=next((c for c in draft['courses'] if c['course']==course),None);options=decks.get(course,[]);ids=[d['id'] for d in options]
                with st.container(key=key+'course_'+course):
                    course_col,deck_col,end_col=st.columns(row_widths,vertical_alignment='center')
                    course_col.markdown('**'+course+'**')
                    course_col.caption(f"{len(options)} deck{'s' if len(options)!=1 else ''} available")
                    picked=deck_col.multiselect('Decks to study',ids,default=[d for d in (old['decks'] if old else []) if d in ids],format_func=lambda i,options=options:next(f"{d['name']} · {d['count']} questions" for d in options if d['id']==i),key=key+'decks_'+course,label_visibility='collapsed',placeholder='Choose decks')
                    end=end_col.date_input('Finish by (exam or target date)',value=max(date.fromisoformat(old['end']),today) if old else today+timedelta(days=14),min_value=today,key=key+'end_'+course,label_visibility='collapsed')
                    if not options:st.warning('You have no Study decks for this course yet.')
                    with st.expander('Start later (optional)'):
                        begin=st.date_input('Start studying on',value=max(date.fromisoformat(old['start']),today) if old and old.get('start') else today,min_value=today,key=key+'start_'+course,help='Today means you start right away. Pick a later day to begin closer to the exam.')
                    start=begin.isoformat() if begin>today else None
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
                        st.markdown('**'+goal_text[value][1]+'**')
                        st.caption(goal_text[value][0])
                        if value==2:st.markdown(':violet-badge[Recommended]')
                        # The button covers the whole card (see study-plan.css), so the card itself is clickable.
                        if st.button(goal_text[value][1],key=key+f'goal_{value}',use_container_width=True):
                            st.session_state[target_key]=value;st.rerun()
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
            for day_col,day in zip(st.columns([1]*7+[2.6]),range(7)):
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
            *session_cols,time_area=st.columns([.8,.8,.8,6],vertical_alignment='bottom')
            for session_col,amount in zip(session_cols,(1,2,3)):
                with session_col:
                    if st.button(str(amount),key=key+f'session_{amount}',type='primary' if sessions==amount else 'secondary',use_container_width=True):
                        st.session_state[sessions_key]=amount;st.rerun()
            times=[]
            for i,col in enumerate(time_area.columns(3)[:sessions]):
                suggested=draft['times'][i] if i<len(draft['times']) else rules.DEFAULT_TIMES[i]
                times.append(col.time_input(f'Session {i+1} starts at',value=time.fromisoformat(suggested),step=900,key=key+f'time_{i}').strftime('%H:%M'))
            st.caption('A session is one sitting in Study Mode. Splitting a day into 2 or 3 sessions keeps each sitting short; every session gets its own start time and calendar entry.')
    plan={'name':name,'target':target,'sessions':sessions,'times':times,'weekdays_off':weekdays_off,'dates_off':dates_off,'courses':chosen};clean=None
    try:clean=rules.validate_plan(plan,profile['courses'],decks,today)
    except ValueError as exc:validation_error=str(exc)
    else:validation_error=''
    levels=None;schedule={}
    if clean:
        levels=study_plan_levels(client,clean,decks)
        if levels is not None:schedule=rules.plan_schedule(clean,levels,today)
    with preview:
        if validation_error:
            checklist=rules.plan_checklist(plan,today)
            with st.container(border=True,key='study_plan_preview_checklist'):
                st.subheader('Live preview')
                if not all(done for _,done in checklist):
                    st.markdown('**To save this plan**')
                    for label,done in checklist:
                        st.markdown((':green[:material/check_circle:] ' if done else ':material/radio_button_unchecked: ')+label)
                st.info(validation_error)
        elif levels is not None:
            study_plan_live_preview(rules,clean,levels,today,schedule)
            with st.container(border=True,key='study_plan_editor_workload'):
                st.write('**Your workload**')
                for item in clean['courses']:st.write(study_plan_workload_text(rules,clean,item,levels[item['course']],today,schedule))
                if len(clean['courses'])>1 and schedule:st.write(study_plan_total_text(schedule))
            st.caption(
                ':material/event: After saving, you can download a calendar file. '
                'Direct Google Calendar sync is available to registered Google test accounts.'
            )
        else:st.info('Choose courses, decks and dates to see the live preview.')
    with actions:
        cancel=st.button('Cancel')
        save=st.button('Save study plan',type='primary',disabled=clean is None)
    if save:
        payload={'plan':clean}
        if draft.get('id'):payload['id']=draft['id']
        saved=study_plan_request(client,'save',payload)
        if saved is not None:
            study_plan_close_editor();st.session_state.study_plan_finish=saved['id'];st.rerun()
    if cancel:
        study_plan_close_editor();st.rerun()
    if draft.get('id'):
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
            if recorded:
                st.caption(f'{len(recorded)} entries of this plan are in your Google Calendar. Remove them first if you no longer want them.')
                study_plan_calendar_action('Remove from Google Calendar','clear',draft['id'],user_id)
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
            wanted = {event['uid']: event for event in events}
            obsolete = []
            for record in stored['calendar_events']:
                event = wanted.get(record['uid'])
                if event is None or 'event_id' in event:
                    obsolete.append(record)
                else:
                    event['event_id'] = record['event_id']
            left = google.remove_events(http, token, obsolete)
            if events:
                created, failed = google.add_events(http, token, events)
        if study_plan_request(client,'events',{'id':stored['id'],'events':left+created}) is None:return
        if left or failed:st.warning(f"Google Calendar was only partly updated for {plan['name']}: {len(events)-failed} entries synced, {failed} could not be synced and {len(left)} old entries could not be removed. Choose Update Google Calendar to try again.")
        elif request['kind']=='sync':st.success(f"Google Calendar now has {len(created)} entries for {plan['name']}.")
        else:st.success(f"The Google Calendar entries for {plan['name']} were removed.")
    except ValueError as exc:st.error(str(exc))
    except httpx.HTTPError:st.error('Google Calendar could not be reached. Retry the sync or download the Calendar file.')


def study_plan_calendar_action(label,kind,plan_id,user_id):
    import google_calendar as google
    notice = 'Google Calendar sync is in testing. Only registered Google test accounts have access.'
    client_id,secret,redirect=study_plan_google_settings()
    with st.popover(label,icon=':material/event:',width='stretch',key=f'plan_google_{kind}_{plan_id}'):
        st.markdown(notice)
        if kind=='sync':
            st.write('For any other account, download the calendar file and import it into your calendar.')
        if client_id and secret:
            state=google.sign_state(secret,kind,plan_id,user_id)
            st.link_button('Continue with a registered test account',google.authorization_url(client_id,redirect,state))
        else:
            st.caption('Google sign-in is unavailable on this app instance.')
    st.caption(notice)


def study_plan_calendar_buttons(plan,recorded,levels,today,user_id):
    """Calendar file download and Google Calendar link for one saved plan."""
    import study_plan as rules
    download,online=st.columns(2)
    download.download_button('Calendar file',rules.plan_ics(plan,rules.plan_sessions(plan,levels,today)),file_name='uniarena-'+plan['id'][:8]+'.ics',mime='text/calendar',key='plan_ics_'+plan['id'],icon=':material/download:',use_container_width=True,help='Download the planned sessions and import them into any calendar.')
    with online:
        study_plan_calendar_action('Update Google Calendar' if recorded else 'Add to Google Calendar','sync',plan['id'],user_id)
    if recorded:
        st.caption(f'{len(recorded)} calendar entries were previously added for this plan.')


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
    st.caption('Download a calendar file for your sessions, or choose Finish to see your progress.')
    study_plan_calendar_buttons(plan,stored.get('calendar_events') or [],levels,today,user_id)
    if st.button('Finish',type='primary',use_container_width=True):
        st.session_state.pop('study_plan_finish',None);st.rerun()


def study_plan_screen(client,profile,user_id=''):
    from datetime import date
    import google_calendar as google
    import study_plan as rules
    study_plan_design()
    st.title('Study Plan')
    decks=study_plan_decks(client)
    if decks is None:return
    study_plan_google_answer(client,decks,user_id)
    if 'plan_draft' in st.session_state:return study_plan_editor(client,profile,decks,user_id)
    data=study_plan_request(client,'list')
    if data is None:return
    saved=next((p for p in data['plans'] if p['id']==st.session_state.get('study_plan_finish')),None)
    if saved:return study_plan_finish(client,saved,decks,user_id)
    with st.container(horizontal=True,vertical_alignment='bottom'):
        st.markdown('<p class="study-plan-intro">Plan your Study Mode sessions until your exams and follow your progress.</p>',unsafe_allow_html=True)
        create=st.button('Create study plan',type='primary',icon=':material/add:')
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
            with st.container(border=True,key='study_plan_today_'+plan['id']):
                study_plan_today(client,plan,levels,by_deck,decks,today,'plan')
            st.write('**Progress towards your exams**')
            if len(plan['courses'])>1:
                everything=[level for item in plan['courses'] for level in levels[item['course']]];overall=rules.plan_progress(everything,plan['target'])
                st.progress(overall,text=f"Overall progress {overall:.0%}")
            for item in plan['courses']:
                share=rules.plan_progress(levels[item['course']],plan['target']);st.progress(share,text=f"{item['course']} {share:.0%} · finish by {date.fromisoformat(item['end']):%d %b}")


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
            if cols[1].button('Open',key='study_resume_'+s['id']):open_round('study', s['id'], fresh=False)
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
    deck_ids=[d['id'] for d in choices]
    preselected=st.session_state.pop('study_deck_preselection',None)
    selected_index=deck_ids.index(preselected) if preselected in deck_ids else 0
    selected_id=st.selectbox('Select quiz deck',deck_ids,index=selected_index,format_func=lambda x:next(d['name']+(' · Shared with me' if d['shared'] else '') for d in choices if d['id']==x))
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
            st.session_state.pop('study_request_id',None);st.session_state.pop('study_invite_friend',None)
            open_round('study', r['id'], fresh=True)


def open_round(mode, session_id, *, fresh):
    """Only a successful start action schedules the intro; reopening never does."""
    st.session_state[f'{mode}_session'] = session_id
    st.session_state.pop('pending_round_intro', None)
    if fresh:
        st.session_state.pending_round_intro = (mode, session_id)
    if mode == 'battle':
        st.session_state.play_mode_preview = 'Battle'
        st.session_state.pop('battle_feedback', None)
    st.rerun()


def show_round_intro(mode, session_id):
    if st.session_state.pop('pending_round_intro', None) == (mode, session_id):
        stage = st.empty()
        stage.html(countdown_overlay(mode))
        time.sleep(INTRO_SECONDS)
        stage.empty()


def resume_study_session(session):
    st.session_state.study_active=True;st.session_state.study_choice='Study alone' if session['mode']=='solo' else 'Study together'
    open_round('study', session['id'], fresh=False)


def show_more_history():
    st.session_state.sessions_history_limit=st.session_state.get('sessions_history_limit',5)+10


def session_card(client,kind,session):
    """One ongoing Battle or Study session with its progress, turn and resume action."""
    with st.container(border=True,key=f"session_card_{kind}_{session['id']}"):
        if kind=='battle':
            st.markdown(':material/swords: **'+session['deck_name']+'**')
            st.caption(f"Battle · {session['course']} · {session['language']} · 15 questions")
            if session['status']=='pending':
                st.progress(1.0);st.markdown(":orange-badge[:material/hourglass_top: Opponent's turn]")
                st.caption('Your answers are saved. Waiting for your opponent.')
            else:st.markdown(':violet-badge[Your turn]' if session.get('started') else ':blue-badge[Ready to start]')
            if st.button('Resume Battle' if session.get('started') else 'Start Battle',key='home_battle_'+session['id'],use_container_width=True):
                open_round('battle', session['id'], fresh=not session.get('started'))
            return
        st.markdown(':material/menu_book: **'+session['name']+'**')
        if session['mode']!='solo':session_partner_chat(client,'study',session['id'],'home')
        st.caption(('Study alone' if session['mode']=='solo' else 'Study together')+f" · {session['cursor']} / {session['count']} answered")
        st.progress(min(1.0,session['cursor']/session['count']) if session.get('count') else 0.0)
        if session['state']=='waiting':st.markdown(':gray-badge[Waiting for a study partner]')
        else:st.markdown(':green-badge[Your turn]')
        if session.get('deadline'):
            from logic import time_left_text
            st.caption('Finish by '+session['deadline']+' · '+(time_left_text(session['deadline']) or ''))
        if st.button('Open Study' if session['state']=='waiting' else 'Resume Study',key='home_study_'+session['id'],use_container_width=True):
            resume_study_session(session)


def ongoing_sessions(client):
    """Study Mode dashboard: continuation, session history and Study Plan to-dos."""
    from logic import STUDY_ONGOING_STATES,session_continue_pick,session_history_rows,time_left_text
    study_data=study_request(client,'list')
    st.html('<style>'+(Path(__file__).parent/'assets'/'sessions.css').read_text()+'</style>')
    study_sessions=(study_data or {}).get('sessions',[])
    study_ongoing=[s for s in study_sessions if s['state'] in STUDY_ONGOING_STATES]
    study_finished=[s for s in study_sessions if s['state'] not in STUDY_ONGOING_STATES]
    st.subheader('Your study sessions')
    main,side=st.columns([2.3,1],gap='large')
    with main:
        pick=session_continue_pick([],study_ongoing)
        if pick:
            session=pick['session']
            with st.container(border=True,key='sessions_continue'):
                text,action=st.columns([3,1.2],vertical_alignment='center')
                with text:
                    left=time_left_text(session.get('deadline'))
                    st.caption('Continue where you left off'+(' · '+left if left else ''))
                    st.markdown('**'+session['name']+'**')
                    st.caption(('Study alone' if session['mode']=='solo' else 'Study together')+f" · {session['cursor']} / {session['count']} answered")
                    st.progress(min(1.0,session['cursor']/session['count']) if session.get('count') else 0.0)
                if action.button('Resume',key='continue_session',icon=':material/play_arrow:',type='primary',use_container_width=True):resume_study_session(session)
        st.subheader('Ongoing study sessions')
        cards=[('study',session) for session in study_ongoing]
        if not cards:st.caption('No ongoing sessions. Start a new one above.')
        else:st.caption(f"{len(cards)} active")
        for row in range(0,len(cards),2):
            for column,(kind,session) in zip(st.columns(2),cards[row:row+2]):
                with column:session_card(client,kind,session)
        st.subheader('Study history')
        rows=session_history_rows([],study_finished)
        if not rows:st.caption('No finished sessions yet. Your results will appear here.')
        else:
            widths=[.9,2.6,1.9,.8,.6,2.1]
            for column,label in zip(st.columns(widths),['Result','Deck','Mode','Score','XP','']):column.caption(label)
            limit=st.session_state.get('sessions_history_limit',5)
            for item in rows[:limit]:
                with st.container(key=f"history_row_{item['kind']}_{item['id']}"):
                    result,deck,mode,score,xp,action=st.columns(widths,vertical_alignment='center')
                    result.markdown(f":{item['tone']}-badge[{item['result']}]")
                    deck.markdown(item['deck'])
                    with mode:
                        if item['kind']=='study' and item['session']['mode']!='solo':session_partner_chat(client,'study',item['id'],'history')
                        else:st.markdown(item['mode'])
                    score.markdown(item['score']);xp.markdown(item['xp'])
                    if action.button('View Study session',key='history_study_'+item['id'],use_container_width=True):
                        st.session_state.study_active=True;open_round('study', item['id'], fresh=False)
            if len(rows)>limit:st.button('Show more',key='sessions_history_more',on_click=show_more_history,use_container_width=True)
    with side:
        with st.container(key='sessions_stat_study'):
            st.caption('Study sessions finished')
            st.markdown(f"### {sum(1 for s in study_finished if s['state']=='completed')}")
            st.caption(f"{sum(s.get('cursor',0) for s in study_sessions)} questions answered in Study sessions")
        study_plan_play_todos(client,study_data)


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


def battle_overview(answers,current_index,flash_index=None,streak=0):
    from battle_ui import battle_progress_tiles
    symbols={'correct':inline_icon('check'),'incorrect':inline_icon('close'),'current':'•','open':''}
    tiles=battle_progress_tiles(answers,current_index)
    markup=''.join(f'<span class="battle-tile battle-tile-{tile["state"]}{" round-tile-flash" if flash_index==tile["number"]-1 else ""}" aria-label="Question {tile["number"]}: {tile["state"]}">{symbols[tile["state"]] or tile["number"]}</span>' for tile in tiles)
    badge=streak_badge(streak)
    foot=('<div class="round-overview-foot">'+badge+'</div>' if badge else '')+combo_markup(streak)
    st.html('<aside class="battle-overview"><div class="round-overview-head"><h3>Overview</h3>'+accuracy_chip(answers)+'</div><div class="battle-overview-grid">'+markup+'</div>'+foot+'<div class="battle-legend"><span><i class="correct"></i>Correct</span><span><i class="incorrect"></i>Incorrect or time expired</span></div></aside>')


@st.fragment(run_every='1s')
def battle_timer(client,session_id,index,server_seconds):
    """Refresh only the countdown; the question and answers stay mounted."""
    from battle_ui import countdown_seconds,timer_tick_fractions
    key=f'battle_timer_{session_id}'
    timer=st.session_state.get(key)
    if not timer or timer.get('index')!=index:
        timer={'index':index,'started_at':time.monotonic(),'server_seconds':server_seconds,'expired':False}
        st.session_state[key]=timer
    seconds=countdown_seconds(timer['server_seconds'],time.monotonic()-timer['started_at'])
    if seconds==0 and not timer['expired']:
        timer['expired']=True
        result=battle_request(client,'round',{'id':session_id})
        if result and result.get('state')=='feedback':
            st.session_state.battle_feedback={**result,'id':session_id}
            st.session_state[f'battle_timeout_notice_{session_id}']=True
            st.rerun(scope='app')
    start,end=timer_tick_fractions(seconds);urgent=' urgent' if seconds<=5 else ' warning' if seconds<=15 else ''
    st.html(f'<div class="battle-timer-track" role="progressbar" aria-label="Time remaining" aria-valuemin="0" aria-valuemax="30" aria-valuenow="{seconds}"><div class="battle-timer-fill{urgent}" style="--timer-start:{start*100:.3f}%;--timer-end:{end*100:.3f}%"></div></div><p class="battle-timer-label">{seconds} seconds</p>')


def return_to_battle_menu(message=None):
    if message:st.session_state.battle_notice=message
    for key in ('battle_session','battle_feedback','battle_new_setup','battle_rating_session'):
        st.session_state.pop(key,None)
    st.session_state.play_mode_preview='Battle'
    st.rerun()


def battle_leave_control(client,session_id):
    """An explicit abandon action; the server records the resulting loss.

    The confirmation is a centred modal over a dimmed round, not a dropdown."""
    if st.button('Leave',icon=':material/swords:',key=f'battle_exit_{session_id}',use_container_width=True):
        st.session_state.round_leave_prompt=session_id;st.rerun()
    if st.session_state.get('round_leave_prompt')==session_id:
        st.html('<div class="round-modal-backdrop"></div>')
        with st.container(key=f'round_leave_modal_{session_id}'):
            st.html('<p class="round-modal-title">Leave the Battle?</p><p class="round-modal-text">Leaving counts as a loss and your opponent wins. Your question timer keeps running while you decide.</p>')
            stay,leave=st.columns(2)
            if stay.button('Keep fighting',key=f'round_leave_stay_{session_id}',use_container_width=True):
                st.session_state.pop('round_leave_prompt',None);st.rerun()
            if leave.button('Leave Battle',key=f'round_leave_confirm_{session_id}',use_container_width=True):
                if battle_request(client,'abandon',{'id':session_id,'confirmed':True}) is not None:
                    st.session_state.pop('round_leave_prompt',None)
                    st.session_state.pop(f'battle_timer_{session_id}',None)
                    st.session_state.pop(f'battle_timeout_notice_{session_id}',None)
                    return_to_battle_menu('You left the Battle. It was recorded as a loss.')


@st.dialog('Battle review',width='large')
def battle_review_dialog(client,session_id):
    result=battle_request(client,'review',{'id':session_id})
    if result is None:return
    st.html('<style>'+(Path(__file__).parent/'assets'/'round-effects.css').read_text()+'</style>')
    answers={item['index']:item for item in result['answers'] if isinstance(item.get('index'),int)}
    total=len(result['cards'])
    st.html('<div class="round-overview-head"><h3>Your round</h3><span class="round-acc">'+str(result['score'])+'<small>/ '+str(total)+'</small></span></div>')
    st.caption('Click a question to review it.')
    if st.session_state.get('battle_review_session')!=session_id:
        st.session_state.battle_review_session=session_id
        st.session_state.battle_review_selected=next((i for i in range(total) if not (answers.get(i) or {}).get('correct')),0)
    selected=st.session_state.get('battle_review_selected',0)
    columns=st.columns(5)
    for index in range(total):
        answer=answers.get(index)
        state='correct' if answer and answer.get('correct') else 'incorrect'
        icon=':material/check:' if state=='correct' else ':material/close:'
        if columns[index%5].button(str(index+1),key=f'review_tile_{state}_{session_id}_{index}',icon=icon,type='primary' if selected==index else 'secondary',use_container_width=True,help=f'Question {index+1}'):
            st.session_state.battle_review_selected=index;st.rerun(scope='fragment')
    if 0<=selected<total:
        card=result['cards'][selected];answer=answers.get(selected)
        status='Not answered' if answer is None else 'Time expired' if answer.get('timed_out') else 'Correct' if answer.get('correct') else 'Incorrect'
        rows=''
        for option in card['answers']:
            own=answer is not None and answer.get('answer_id')==option['id']
            if option['id']==card['correct_answer_id']:
                rows+='<span class="round-review-a ok">'+escape(option['text'])+(' — Your answer' if own else '')+'</span>'
            elif own:
                rows+='<span class="round-review-a bad">Your answer: '+escape(option['text'])+'</span>'
            else:
                rows+='<span class="round-review-a">'+escape(option['text'])+'</span>'
        st.html('<div class="round-review-q"><b>Q'+str(selected+1)+' · '+escape(card['question'])+'</b><span class="round-review-a">'+status+'</span>'+rows+'</div>')
        with st.popover('Report this question',key=f'battle_report_question_{session_id}_{selected+1}'):
            battle_question_report_form(client,session_id,selected)


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


def battle_round_screen(client,session_id):
    st.html('<style>'+ (Path(__file__).parent/'assets'/'battle-round.css').read_text()+(Path(__file__).parent/'assets'/'round-effects.css').read_text()+'</style>')
    progress=battle_progress(client,session_id)
    if progress is None:return
    answers=progress.get('answers',[])
    feedback=st.session_state.get('battle_feedback')
    if feedback and feedback.get('id')==session_id:
        card=feedback['card'];response=feedback['feedback']
        streak=streak_length(answers)
        question,overview=st.columns([3,1],gap='large')
        with question:
            st.caption(f"Question {response['index']+1} of 15")
            st.html('<div class="battle-question-card">'+escape(card['question'])+'</div>')
            if response['correct']:st.success('Correct!')
            elif response.get('timed_out'):st.error('Time expired.')
            else:st.error('That answer was incorrect.')
            burst=''.join(f'<span class="round-confetti c{n}"></span>' for n in range(1,9))
            parts=[]
            for answer in display_options(card['answers'],session_id,response['index']):
                text=escape(answer['text'])
                if answer['id']==card['correct_answer_id'] and response['correct']:
                    parts.append('<div class="battle-answer-card round-burst is-correct is-correct-animated">'+text+burst+'<span class="round-xp">+XP</span></div>')
                elif answer['id']==card['correct_answer_id']:
                    parts.append('<div class="battle-answer-card is-correct is-correct-reveal">'+text+'</div>')
                elif answer['id']==response.get('answer_id'):
                    parts.append('<div class="battle-answer-card is-incorrect">'+text+'</div>')
                else:
                    parts.append('<div class="battle-answer-card is-neutral">'+text+'</div>')
            st.html('<div class="battle-answer-grid">'+''.join(parts)+'</div>')
            if not response['correct']:st.html('<div class="round-vignette"></div>')
            elif streak_milestone(streak):st.html('<div class="round-streak-banner">'+streak_milestone(streak)+'</div>')
            if st.button('Continue',type='primary'):
                st.session_state.pop('battle_feedback',None);st.rerun()
        with overview:
            battle_leave_control(client,session_id)
            battle_overview(answers,response['index']+1,flash_index=response['index'],streak=streak)
        if response.get('timed_out') and st.session_state.pop(f'battle_timeout_notice_{session_id}',False):
            st.toast('Time has passed',icon=':material/timer_off:')
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
            streak=streak_length(answers)
            st.html('<div class="battle-question-card">'+escape(result['question'])+'</div>')
            question_tools(f'battle_{session_id}_{result["index"]}',result.get('allow_calculator') is True)
            columns=st.columns(2)
            for i,answer in enumerate(display_options(result['options'],session_id,result['index'])):
                if columns[i%2].button(answer['text'],key=f'battle_answer_{session_id}_{result["index"]}_{answer["id"]}',use_container_width=True):
                    response=battle_request(client,'answer',{'id':session_id,'index':result['index'],'answer_id':answer['id']})
                    if response is not None:
                        st.session_state.battle_feedback={**response,'id':session_id};st.rerun()
            battle_timer(client,session_id,result['index'],result['seconds'])
        with overview:
            battle_leave_control(client,session_id)
            battle_overview(answers,result['index'],streak=streak)
        return
    if state=='finish':
        if battle_request(client,'finish',{'id':session_id}) is not None:
            st.session_state.battle_rating_session=session_id
            st.session_state.pop('battle_session',None)
            st.session_state.pop('battle_feedback',None)
            st.rerun()
        return
    if state=='rating':
        st.session_state.battle_rating_session=session_id
        st.session_state.pop('battle_session',None)
        st.rerun()
        return
    st.info('This Battle is complete.')
    return_to_battle_menu()


@st.dialog('Battle Mode',width='large',dismissible=False)
def battle_game_dialog(client,session_id):
    battle_round_screen(client,session_id)


@st.dialog('Rate this Battle Deck')
def battle_rating_dialog(client,session_id):
    """A completed participant chooses one rating, then returns to Battle home."""
    result=battle_request(client,'round',{'id':session_id})
    if result is None:return
    if result.get('state')!='rating':
        return_to_battle_menu()
        return
    burst=''.join(f'<span class="round-confetti c{n}"></span>' for n in range(1,9)) if result['score']>=8 else ''
    st.html('<style>'+(Path(__file__).parent/'assets'/'round-effects.css').read_text()+'</style><div class="round-score" role="status" aria-label="Correct answers: '+str(result['score'])+' of 15">'+burst+'<span class="round-score-value">'+str(result['score'])+'</span><span class="round-score-total">/ 15 correct</span></div>')
    if not result.get('can_rate'):
        st.info('You played your own Battle Deck. It does not receive a rating from you.')
        if st.button('Back to Battle Mode',type='primary'):return_to_battle_menu()
        return
    labels={'good':'Good','neutral':'Neutral','bad':'Bad'}
    rating=st.radio('How was this Battle Deck?',tuple(labels),format_func=labels.get,index=None,horizontal=True,key=f'battle_rating_{session_id}')
    if rating and battle_request(client,'rate',{'id':session_id,'rating':rating}) is not None:
        return_to_battle_menu()


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
    with st.container(border=True,key='battle_overview_search'):
        st.write('**Finding an opponent**')
        st.caption(f"{search['course']} · {search['language']}")
        st.write('**Time remaining: '+battle_search_timer_text(remaining)+'**')
        st.progress(min(1,remaining/3600),text='Searching for a compatible player')
        if st.button('Cancel search',key='battle_cancel_search'):
            if battle_cancel_search(client) is not None:
                st.session_state.battle_notice='Battle search cancelled.'
                st.rerun()


def battle_session_overview(client,sessions,search=None,invites=(),username=None):
    """Battle dashboard: Ongoing and Pending side by side, Recently completed below."""
    from logic import recent_completed_battles
    me=escape(str(username or 'You')[:1].upper())
    def versus_markup(opponent):
        return ('<div class="bo-vs"><span class="bo-av bo-av-me">'+me+'</span><i>VS</i>'
                '<span class="bo-av bo-av-op">'+escape(str(opponent)[:1].upper())+'</span><b>'+escape(str(opponent))+'</b></div>')
    def deck_markup(name):
        safe=escape(str(name),quote=True)
        return '<p class="bo-deck" title="'+safe+'">'+safe+'</p>'
    with st.container(border=True,key='battle_game_overview'):
        st.subheader('Game Overview')
        for column,(label,icon,status) in zip(st.columns(2,gap='medium'),(('Ongoing','swords','ongoing'),('Pending','hourglass','pending'))):
            rows=[session for session in sessions if session['status']==status]
            pending_invites=list(invites) if status=='pending' else []
            count=len(rows)+(1 if status=='pending' and search else 0)+len(pending_invites)
            with column:
                with st.container(key=f'battle_overview_group_{status}'):
                    st.html(f'<p class="battle-overview-column-heading"><span class="bo-ic">{inline_icon(icon)}</span>{label}<b>{count}</b></p>')
                    if not count:
                        empty_icon='shield' if status=='ongoing' else icon
                        st.html(f'<div class="bo-empty">{inline_icon(empty_icon)}<div>No {status} Battles.</div></div>')
                    if status=='pending' and search:battle_pending_search(client,search)
                    for invite in pending_invites:
                        invite_key='battle_overview_invite_received_' if invite['incoming'] else 'battle_overview_invite_sent_'
                        with st.container(border=True,key=invite_key+invite['id']):
                            direction='Invitation received' if invite['incoming'] else 'Invitation sent'
                            deck_name=str(invite.get('deck_name') or 'Random Deck')
                            safe_deck=escape(deck_name,quote=True)
                            if invite['incoming']:
                                st.html('<div class="battle-overview-card-copy battle-invite-received"><span class="battle-invite-new">'+inline_icon('sparkles')+' New</span><strong title="'+safe_deck+'">'+safe_deck+'</strong><p class="battle-invite-sender">'+escape(str(invite['username']))+'</p><p>'+escape(str(invite['course']))+'</p></div>')
                            else:
                                st.html('<div class="battle-overview-card-copy"><strong title="'+safe_deck+'">'+safe_deck+'</strong><p>'+escape(direction.upper()+' · '+invite['username'])+'</p><p>'+escape(str(invite['course']))+'</p></div>')
                            if invite['incoming']:
                                accept,decline=st.columns(2)
                                if accept.button('Accept',key='battle_accept_'+invite['id'],type='primary',use_container_width=True):
                                    result=battle_request(client,'accept_invite',{'invite_id':invite['id']})
                                    if result is not None:open_round('battle', result['session_id'], fresh=True)
                                if decline.button('Decline',key='battle_decline_'+invite['id'],use_container_width=True):
                                    if battle_request(client,'decline_invite',{'invite_id':invite['id']}) is not None:st.rerun()
                            elif st.button('Cancel invitation',key='battle_cancel_'+invite['id'],use_container_width=True):
                                if battle_request(client,'cancel_invite',{'invite_id':invite['id']}) is not None:st.rerun()
                    for session in rows:
                        opponent=session.get('opponent_username','Unknown opponent')
                        with st.container(border=True,key=f'battle_overview_card_{status}_{session["id"]}'):
                            if status=='ongoing':
                                st.html(versus_markup(opponent)+deck_markup(session['deck_name']))
                                st.markdown(':violet-badge[:material/schedule: Your turn]')
                                if st.button('Resume Battle' if session.get('started') else 'Start Battle',key='overview_battle_'+session['id'],type='primary',use_container_width=True):
                                    open_round('battle', session['id'], fresh=not session.get('started'))
                            else:
                                st.html(versus_markup(opponent)+deck_markup(session['deck_name'])
                                 +f'<div class="bo-score"><b>{session["score"]}</b><i>/ 15</i><span class="bo-pill bo-xp-plus">your result</span></div>'
                                 +'<div class="bo-wait"><span></span>Waiting for '+escape(str(opponent))+'…</div>')
        completed=recent_completed_battles(sessions)
        with st.container(key='battle_overview_group_completed'):
            st.html(f'<p class="battle-overview-column-heading"><span class="bo-ic">{inline_icon("flag")}</span>Recently completed<b>{len(completed)}</b></p>')
            if not completed:st.html('<div class="bo-empty">'+inline_icon('flag')+'No completed Battles yet.</div>')
            columns=st.columns(3,gap='medium')
            for index,session in enumerate(completed):
                opponent=session.get('opponent_username','Unknown opponent')
                with columns[index%3]:
                    with st.container(border=True,key=f'battle_overview_card_completed_{session["id"]}'):
                        opponent_score=session.get('opponent_score')
                        score=f"{session['score']} : {opponent_score}" if opponent_score is not None else f"{session['score']} / 15"
                        result=str(session.get('result') or 'completed').title()
                        xp=session.get('game_xp_delta',0)
                        xp_class='bo-xp-plus' if xp>0 else 'bo-xp-minus'
                        trophy=inline_icon('trophy') if result=='Win' else ''
                        st.html(versus_markup(opponent)+deck_markup(session['deck_name'])
                         +f'<div class="bo-score"><b>{score}</b><span class="bo-pill bo-{result.lower()}">{trophy}{result}</span><span class="bo-pill {xp_class}">{xp:+d} XP</span></div>')
                        if st.button('Review questions',key='overview_battle_review_'+session['id'],use_container_width=True):battle_review_dialog(client,session['id'])


def battle_session_history(client,sessions):
    """Show completed Battle results in a compact history table using stored values only."""
    completed=[session for session in sessions if session['status']=='completed']
    with st.container(border=True,key='battle_session_history'):
        title,filters=st.columns([4,1.7],vertical_alignment='center')
        with title:st.subheader('Battle history')
        with filters:
            selected=st.segmented_control('Result filter',('All','Wins','Losses'),default='All',label_visibility='collapsed',key='battle_history_filter')
        if selected=='Wins':completed=[session for session in completed if session.get('result')=='win']
        if selected=='Losses':completed=[session for session in completed if session.get('result')=='loss']
        if not completed:st.caption('No completed Battles match this filter.')
        for session in completed:
            opponent=session.get('opponent_username','Unknown opponent')
            opponent_score=session.get('opponent_score')
            score=f"{session['score']} : {opponent_score}" if opponent_score is not None else f"{session['score']} / 15"
            result=str(session.get('result') or 'completed').title()
            outcome,deck,opponent_cell,score_cell,xp,review=st.columns([1.05,2.8,1.65,.85,.7,1.25],vertical_alignment='center')
            with outcome:st.markdown(f'<span class="battle-history-result battle-overview-result-{result.lower()}">{result}</span>',unsafe_allow_html=True)
            with deck:st.write('**'+session['deck_name']+'**')
            with opponent_cell:st.caption('vs. '+opponent)
            with score_cell:st.write(score)
            with xp:st.markdown(f'**{session.get("game_xp_delta",0):+d} XP**')
            with review:
                if st.button('Review Battle',key='history_battle_review_'+session['id'],use_container_width=True):battle_review_dialog(client,session['id'])


def battle_dashboard_rank(client):
    """Read the authenticated player's real Battle-XP rank without blocking Battle."""
    from db import LeaderboardRepository
    try:data=LeaderboardRepository(client).load()
    except ValueError:return None
    rank=(data.get('me') or {}).get('rank') if isinstance(data,dict) else None
    return rank if isinstance(rank,int) and rank>0 else None


def battle_dashboard_hero(client,profile,sessions):
    """Battle summary uses durable Battle XP and completed results only."""
    from logic import battle_record,xp_breakdown
    record=battle_record(sessions)
    xp=xp_breakdown(profile)['battle']
    rank=battle_dashboard_rank(client)
    rank_html=f'<div><strong>#{rank}</strong><span>Leaderboard</span></div>' if rank is not None else ''
    streak_html=f'<div><strong>{int(profile.get("win_streak",0) or 0)}</strong><span>Win streak</span></div>'
    with st.container(key='battle_dashboard_hero'):
        details,action=st.columns([4,1],vertical_alignment='center')
        with details:
            st.subheader('Battle Mode')
            st.caption('15 shared questions · 30 seconds per question · Battle XP')
            st.html(f'<div class="battle-hero-metrics"><div><strong>{xp:,}</strong><span>Battle XP</span></div><div><strong>{record["wins"]} / {record["losses"]}</strong><span>Wins / Losses</span></div>{rank_html}{streak_html}</div>')
        with action:
            if st.button('New Battle',key='hero_new_battle',type='primary',icon=':material/add:',use_container_width=True):
                st.session_state.battle_new_setup=True;st.rerun()


def battle_new_setup_screen(client,profile):
    st.html('<style>'+(Path(__file__).parent/'assets'/'battle-overview.css').read_text()+'</style>')
    st.subheader('Start a new Battle')
    if st.button('Back to Game Overview',key='close_new_battle',icon=':material/arrow_back:'):
        st.session_state.pop('battle_new_setup',None);st.session_state.pop('battle_invite_friend',None);st.rerun()
    with st.container(key='battle_new_setup'):
        st.html('<p class="battle-setup-step">1 · Course &amp; language</p>')
        course_column,language_column=st.columns([2,1])
        with course_column:course=st.selectbox('Course',profile['courses'],key='battle_course')
        with language_column:language=st.selectbox('Language',profile['languages'],key='battle_language')
        st.html('<p class="battle-setup-step">2 · Deck</p>')
        random_source,top_source=st.columns(2)
        source=st.session_state.get('battle_deck_source','Random Deck')
        with random_source:
            if st.button('Random Deck',key='battle_source_random',icon=':material/casino:',use_container_width=True,type='primary' if source=='Random Deck' else 'secondary'):
                st.session_state.battle_deck_source='Random Deck';st.session_state.pop('battle_top_deck',None);st.rerun()
        with top_source:
            if st.button('Top Decks',key='battle_source_top',icon=':material/star:',use_container_width=True,type='primary' if source=='Top Decks' else 'secondary'):
                st.session_state.battle_deck_source='Top Decks';st.rerun()
    selected=None
    availability=None
    if source=='Top Decks':
        top=battle_request(client,'top',{'course':course,'language':language})
        ranked=(top or {}).get('decks',[])
        if ranked:
            ranked=ranked[:10]
            selected=st.session_state.get('battle_top_deck')
            if selected not in {item['id'] for item in ranked}:
                selected=ranked[0]['id'];st.session_state.battle_top_deck=selected
            st.html('<p class="battle-top-decks-label">Top Decks</p>')
            for position in range(1,11):
                if position<=len(ranked):
                    item=ranked[position-1]
                    medal_icon=':material/military_tech:' if position<=3 else None
                    with st.container(key='battle_top_deck_row_'+item['id']):
                        deck_name,rating=st.columns([8,1],vertical_alignment='center')
                        with deck_name:
                            if st.button(f'{position}. {item["name"]}',key='battle_top_deck_'+item['id'],icon=medal_icon,use_container_width=True,type='primary' if selected==item['id'] else 'secondary'):
                                st.session_state.battle_top_deck=item['id'];st.rerun()
                        with rating:
                            st.html(f'<span class="battle-top-deck-rating">{item["rating_count"]} ratings</span>')
        else:st.info('No eligible Battle Deck is available for the selected course and language.')
        for position in range(len(ranked)+1,11):st.button(f'{position}. Outstanding',disabled=True,key='battle_outstanding_'+str(position),use_container_width=True)
    else:
        availability=battle_deck_availability(client,course,language)
        if availability is not None and not availability['available']:
            st.warning('No available Battle Decks yet for the selected course and language. Create a Battle Deck first or choose different criteria.')
    st.html('<p class="battle-setup-step">3 · Opponent</p>')
    random_opponent,friend_opponent=st.columns(2)
    opponent=st.session_state.get('battle_opponent','Random player')
    with random_opponent:
        if st.button('Random player',key='battle_opponent_random',icon=':material/public:',use_container_width=True,type='primary' if opponent=='Random player' else 'secondary'):
            st.session_state.battle_opponent='Random player';st.rerun()
    with friend_opponent:
        if st.button('Friend',key='battle_opponent_friend',icon=':material/groups:',use_container_width=True,type='primary' if opponent=='Friend' else 'secondary'):
            st.session_state.battle_opponent='Friend';st.rerun()
    payload={'course':course,'language':language,'source_kind':'random' if source=='Random Deck' else 'top'}
    if selected:payload['deck_id']=selected
    can_start=not (source=='Random Deck' and (availability is None or not availability['available']))
    if opponent=='Random player':
        if st.button('Find random player',type='primary',disabled=not can_start or (source=='Top Decks' and selected is None)):
            result=battle_request(client,'join',payload)
            if result is not None:
                if result.get('session_id'):open_round('battle', result['session_id'], fresh=True)
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
    if rating_session:=st.session_state.get('battle_rating_session'):
        battle_rating_dialog(client,rating_session);return
    if st.session_state.get('battle_session'):
        show_round_intro('battle',st.session_state.battle_session)
        battle_game_dialog(client,st.session_state.battle_session);return
    if st.session_state.get('battle_new_setup'):
        battle_new_setup_screen(client,profile);return
    state=battle_request(client,'list')
    if state is None:return
    st.html('<style>'+(Path(__file__).parent/'assets'/'battle-overview.css').read_text()+'</style>')
    battle_dashboard_hero(client,profile,state.get('sessions',[]))
    if notice:=st.session_state.pop('battle_notice',None):st.success(notice)
    battle_session_overview(client,state.get('sessions',[]),state.get('search'),state.get('invites',[]),profile.get('username'))
    battle_session_history(client,state.get('sessions',[]))


def incoming_battle_invite_count(client):
    """Return the authenticated player's currently actionable Battle invitations."""
    try:state=battle_request(client,'list')
    except Exception:return 0
    if not isinstance(state,dict):return 0
    return sum(1 for invite in state.get('invites',[]) if invite.get('incoming'))


LEADERBOARD_STYLE='<style>.sd-lb-row{display:flex;align-items:center;gap:12px;padding:8px 12px;border-top:1px solid var(--sd-border)}.sd-lb-row img{width:40px;height:40px;border-radius:50%;object-fit:cover}.sd-lb-place{width:44px}.sd-lb-identity{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}.sd-lb-name{font-weight:600}.sd-lb-university{color:var(--sd-muted);font-size:.86rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.sd-lb-xp{white-space:nowrap}.sd-lb-me{background:var(--sd-hover);border-radius:12px;font-weight:700}</style>'

def leaderboard_rows(rows,repo):
    lines='';cache=st.session_state.setdefault('leaderboard_pictures',{})
    for row in rows:
        path=row.get('image_path')
        if path not in cache:
            try:
                data=repo.image(path);cache[path]=data if isinstance(data,(bytes,bytearray)) else None
            except Exception:cache[path]=None
        image=base64.b64encode(cache[path] or render_avatar(row.get('avatar') or DEFAULT_AVATAR)).decode()
        university=escape(str(row.get('university') or 'University not set'))
        lines+=f'<div class="sd-lb-row{" sd-lb-me" if row.get("me") else ""}"><span class="sd-lb-place">#{int(row["rank"])}</span><img src="data:image/png;base64,{image}" alt=""><span class="sd-lb-identity"><span class="sd-lb-name">{escape(str(row["username"]))}{" (you)" if row.get("me") else ""}</span><span class="sd-lb-university">{university}</span></span><span class="sd-lb-xp">{int(row["xp"])} XP</span></div>'
    st.html(LEADERBOARD_STYLE+'<div>'+lines+'</div>')

def leaderboard_demo(profile):
    names=['nora_k','tiago','lena_m','felix','ines','jonas','sofia_r','matteo','clara','diogo','emma_w','lukas','beatriz','hugo','anna_s'];points=[1840,1675,1520,1520,1390,1210,1085,960,870,790,640,455,320,180,60]
    universities=['Nova SBE','University of Lisbon','University of Porto','Nova SBE','University of Coimbra']
    rows=[{'username':n,'xp':x,'image_path':None,'university':universities[i%len(universities)],'me':False} for i,(n,x) in enumerate(zip(names,points))]+[{'username':profile['username'],'xp':705,'image_path':profile.get('image_path'),'university':profile.get('university'),'me':True}]
    def ranked(items):return [{**item,'rank':1+sum(other['xp']>item['xp'] for other in items)} for item in sorted(items,key=lambda item:(-item['xp'],item['username']))]
    world=ranked(rows)
    campus=profile.get('university')
    return {
        'top':world[:10], 'me':next(item for item in world if item['me']),
        'university':ranked([item for item in rows if campus and item['university']==campus])[:10],
        'friends':ranked([item for item in rows if item['me'] or item['username'] in ('tiago','ines','emma_w','hugo')]),
    }


def leaderboard_screen(client,repo,profile=None):
    from db import LeaderboardRepository
    st.title('Leaderboard')
    rankings=LeaderboardRepository(client)
    demo=profile and os.getenv('LEADERBOARD_DEMO')=='1' and (os.getenv('APP_URL') or '').startswith('http://localhost')
    if demo:
        st.warning('Preview with invented students and XP.');data=leaderboard_demo(profile)
    else:
        try:data=rankings.load()
        except ValueError as exc:st.error(str(exc));return
    st.caption('Ranks are based on Battle XP earned in Battle Mode. Study Mode does not affect them.')
    global_tab,university_tab,friends_tab=st.tabs(['Global top 10','University top 10','Friends'])
    with global_tab:
        top=data.get('top',[])
        leaderboard_rows(top,repo)
        if data.get('me') and not any(row.get('me') for row in top):
            st.caption('Your place')
            leaderboard_rows([data['me']],repo)
    with university_tab:
        # Both sources describe the authenticated player. Earlier leaderboard
        # responses omit university, so use the loaded profile in that case.
        viewer={**(profile or {}), **(data.get('me') or {})}
        if not (viewer.get('university') or '').strip():
            st.caption('Add your university to your profile to see its ranking.')
        else:
            st.text(viewer['university'])
            try:
                campus_rows=data['university'] if demo else rankings.university_top(viewer)
            except ValueError as exc:
                st.error(str(exc))
            else:
                if campus_rows:
                    leaderboard_rows(campus_rows,repo)
                else:
                    st.caption('No students appear in your university ranking yet.')
    with friends_tab:
        friends=data.get('friends',[])
        leaderboard_rows(friends,repo)
        if len(friends)<2:st.caption('Add friends to compare your Battle XP.')


def play_screen(client,profile):
    from db import PlayRepository
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
            st.title('Play')
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
    if not recovery_data and st.query_params.get("code") and "state" not in st.query_params:
        st.caption("Checking your email link…")
        st.stop()
    if recovery_data:
        st.session_state.recovery_received=True
        if recovery_data.get("code") and "state" not in st.query_params:
            st.query_params.pop("code", None)
        result=auth.begin_recovery(recovery_data)
        if result.status=="recovery_ready":
            st.session_state.recovering=True
            st.session_state.used_recovery_proof = recovery_data.get("verifier")
        else:
            if recovery_data.get("code") and not recovery_data.get("verifier"):
                st.session_state.started = True
                st.session_state.browser_loaded = True
                st.session_state.email_link_hint = result.message
            else:
                st.session_state.recovery_error=result.message
        st.rerun()
if st.session_state.get("recovering"):
    if st.session_state.get("used_recovery_proof"):
        store_recovery_proof("clear", st.session_state.used_recovery_proof)
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
if st.session_state.get("email_link_hint"):
    st.info(st.session_state.pop("email_link_hint"))
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
                st.session_state.main_page=saved.get("page") if saved.get("page") in ("Decks","Play","Friends","Leaderboard","Study Plan","Profile","Chats") else "Play"
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
                st.session_state.pop("reset_email_notice", None)
                result=auth.request_password_reset(reset_email)
                if result.status == "check_email":
                    st.session_state.pending_reset_proof = auth.recovery_verifier()
                    st.session_state.reset_proof_expires = int((time.time() + 3600) * 1000)
                    st.session_state.reset_email_notice = result.message
                else:
                    st.error(result.message)
            if st.session_state.get("reset_email_notice"):
                st.success(st.session_state.reset_email_notice)
                st.caption("Open the latest reset email in this browser, using the same browser profile.")
            if st.session_state.get("pending_reset_proof"):
                storage_status = store_recovery_proof(
                    "save", st.session_state.pending_reset_proof, st.session_state.reset_proof_expires
                )
                if storage_status == "saved":
                    del st.session_state.pending_reset_proof
                if storage_status == "storage_unavailable":
                    st.warning("Allow browser storage, then request a fresh reset email.")
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
page=st.session_state.get('main_page','Play')
if str(st.query_params.get('state','')).startswith('sdplan.'):page=st.session_state.main_page='Study Plan'
if profile:
    battle_invites=incoming_battle_invite_count(auth.client)
    with st.container(key='sidebar_navigation'):
        with st.container(key='top_brand'):
            # The logo and wordmark are one button that opens Play; assets/navigation.css gives it the brand look.
            st.html('<style>.st-key-open_home button::before{background-image:url("data:image/png;base64,'+logo_small+'")}</style>')
            if st.button('Uni**Arena**',key='open_home'):
                navigate('Play')
        with st.container(key='sidebar_main_actions'):
            for label in ['Decks','Play','Leaderboard','Study Plan']:
                if label=='Play' and battle_invites:
                    with st.container(key='nav_play_invite_badge'):
                        clicked=st.button(label,key='nav_'+label,type='primary' if page==label else 'secondary',use_container_width=True)
                else:
                    clicked=st.button(label,key='nav_'+label,type='primary' if page==label else 'secondary',use_container_width=True)
                if clicked:
                    navigate(label)
        st.divider()
        with st.container(key='sidebar_account_actions'):
            if st.button('Friends',key='open_friends',type='primary' if page=='Friends' else 'secondary',use_container_width=True):
                navigate('Friends')
            chat_navigation(auth.client, page == 'Chats')
            st.html('<style>'+profile_button_avatar_css(page_speed.thumbnail(picture or page_speed.rendered_avatar(tuple(sorted(DEFAULT_AVATAR.items()))),84))+'</style>')
            if st.button('Profile',key='open_profile',use_container_width=True):
                navigate('Profile')
if profile:
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
    if page=='Chats':
        chats_screen(auth.client, picture)
        st.stop()
    if page=='Play':
        play_screen(auth.client,profile);st.stop()
    if page=='Decks':
        decks_screen(auth.client,profile);st.stop()
    if page=='Friends':
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
