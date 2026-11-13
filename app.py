"""StudyDuel authentication and profile setup."""
import os
from pathlib import Path
from PIL import Image
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
from appearance import apply_appearance
from sharing import share_invitation
from logic import normalize_friend_code, invitation_url, invitation_token
from logic import CATALOG, LANGUAGES, DEFAULT_AVATAR, OPTIONS, DEGREES, render_avatar, crop_photo, validate_username

LOGO_PATH=Path(__file__).parent / "assets" / "studyduel-icon.png"
st.set_page_config(page_title="StudyDuel",page_icon=Image.open(LOGO_PATH),layout="centered")
apply_appearance()
st.markdown("""<style>
.block-container{max-width:940px;padding-top:2.5rem}
[data-testid="stCaptionContainer"]{opacity:1!important;color:var(--sd-muted)!important}
[data-testid="stPopoverBody"] [data-testid="stCaptionContainer"]{color:inherit!important}
h1{letter-spacing:-.04em}div[data-testid="stForm"]{border-radius:18px;padding:24px}
.stButton>button{border-radius:10px}div[data-testid="stMetric"]{background:var(--sd-surface);color:var(--sd-text);border:1px solid var(--sd-border);border-radius:16px;padding:20px;border-top:4px solid #6EE7B7}
</style>""",unsafe_allow_html=True)
st.html('<style>'+(Path(__file__).parent/'assets'/'navigation.css').read_text()+'</style>')
logo_data=base64.b64encode(LOGO_PATH.read_bytes()).decode()
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

def friend_action(friends,action,value=""):
    try:
        result=friends.action(action,value)
        st.session_state.notice=result.get("message","Updated.")
        return result
    except ValueError as exc:
        st.error(str(exc))
        return None

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
    with st.expander("Add a friend by code"):
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
    with st.expander("Invite a friend with a link"):
        if st.button("Create new invitation link"):
            result=friend_action(friends,"create_invite")
            if result:
                st.session_state.share_invite_token=result["token"]
                st.rerun()
        if state.get("invite_expires"):
            st.caption("Your current link expires: "+state["invite_expires"][:10])
            if st.session_state.get("share_invite_token"):
                try:share_invitation(invitation_url(config("PUBLIC_APP_URL") or config("APP_URL") or "http://localhost:8501",st.session_state.share_invite_token))
                except ValueError as exc:st.info(str(exc))
            else:st.caption("Your existing link still works. Create a new link if you need another copy; this replaces the old one.")
            if st.button("Revoke invitation link"):
                if friend_action(friends,"revoke_invite"):
                    st.session_state.pop("share_invite_token",None)
                    st.rerun()
        st.caption("Links expire after seven days. Creating a new link replaces the previous one.")
    for title,items,actions in [("Incoming requests",state["incoming"],[("Accept","accept"),("Decline","decline")]),("Sent requests",state["sent"],[("Cancel request","cancel")]),("Your friends",state["friends"],[("Remove friend","remove")])]:
        st.subheader(f"{title} ({len(items)})")
        if not items:st.caption("Nothing here yet.")
        for item in items:
            with st.container(border=True):
                public_person(item["person"],repo)
                for label,action in actions:
                    if action=="remove":
                        with st.expander("Remove friend"):
                            st.caption("This removes the friendship for both of you.")
                            if st.button("Confirm removal",key="remove_"+item["id"]):
                                if friend_action(friends,action,item["id"]):st.rerun()
                    elif st.button(label,key=action+"_"+item["id"]):
                        if friend_action(friends,action,item["id"]):st.rerun()

def calculator_key(key,token):
    from logic import calculate
    st.session_state.pop(key+'_error',None)
    value=st.session_state.get(key,'')
    if token=='Clear':st.session_state[key]=''
    elif token=='⌫':st.session_state[key]=value[:-1]
    elif token=='=':
        try:st.session_state[key]=calculate(value)
        except ValueError as exc:st.session_state[key+'_error']=str(exc)
    elif len(value)<120:st.session_state[key]=value+token


@st.fragment
def question_calculator(identity):
    key='calculator_'+identity
    with st.popover('Calculator',icon=':material/calculate:'):
        st.caption('Basic arithmetic · +, −, ×, ÷ and brackets')
        st.text_input('Calculation',key=key,max_chars=120,placeholder='e.g. (100 + 20) ÷ 4')
        for row in [('7','8','9','÷'),('4','5','6','×'),('1','2','3','−'),('0','.','(',')'),('Clear','⌫','+','=')]:
            for col,token in zip(st.columns(4),row):
                col.button(token,key=key+'_'+token,on_click=calculator_key,args=(key,token),use_container_width=True)
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


def decks_screen(client,profile):
    from db import DeckRepository
    from logic import new_deck,validate_card,validate_deck,add_card,delete_card
    repository=DeckRepository(client)
    st.title('Decks')
    if st.session_state.get('study_library'):
        if st.button('Back to course decks'):
            st.session_state.pop('study_library');st.rerun()
        study_library(client,profile);return
    if st.button('Study decks & progress',type='primary'):
        st.session_state.study_library=True;st.rerun()
    st.caption('Create questions. Check every answer. Share what you know.')
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
        st.caption('Choose any card to edit it. ✓ means complete; ○ means incomplete.')
        for row in range(0,len(draft['cards']),5):
            columns=st.columns(5)
            for j in range(row,min(row+5,len(draft['cards']))):
                columns[j-row].button(f"{j+1} {'✓' if completed[j] else '○'}",key='choose_'+draft['cards'][j]['id'],on_click=deck_select_card,args=(j,),use_container_width=True)
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
    st.subheader('Create a deck')
    manual,anki,ai=st.columns(3)
    with manual:
        st.write('**Manual**');st.caption('Write your own questions and answers.')
        if st.button('+ Create New Deck',type='primary',use_container_width=True):
            st.session_state.deck_draft=new_deck(profile['courses'][0],profile['languages'][0]);st.session_state.deck_index=0;st.rerun()
    with anki:
        st.write('**Anki import**');st.caption('Coming soon')
        st.button('Import from Anki',disabled=True,use_container_width=True)
    with ai:
        st.write('**AI from lecture slides**');st.caption('Coming soon')
        st.button('Generate with AI',disabled=True,use_container_width=True)
    st.subheader('Your courses')
    st.caption('Decks are shared with signed-in students at your university. Add courses in Edit profile.')
    course=st.selectbox('Browse course',profile['courses'],key='deck_browse_course')
    try:decks=repository.list(course)
    except ValueError as exc:st.error(str(exc));return
    if not decks:st.info('No decks in this course yet. Create the first one.')
    for deck in decks:
        with st.container(border=True):
            st.subheader(deck['name'])
            st.caption(f"By {(deck.get('profiles') or {}).get('username','Student')} · 15 questions · Not rated")
            if st.button('Open deck',key='open_'+deck['id']):
                st.session_state.deck_open=deck['id'];st.rerun()

def play_request(repository,action,data=None):
    try:return repository.action(action,data)
    except ValueError as exc:st.error(str(exc));return None


def navigate(page):
    if st.session_state.get('play_in_round'):
        st.session_state.play_exit_to=page
    else:
        st.session_state.main_page=page
        if page=='Play':
            st.session_state.pop('study_active',None)
            st.session_state.pop('study_choose',None)
    st.rerun()


@st.fragment(run_every='1s')
def play_round_screen(client,duel_id):
    from db import PlayRepository
    repository=PlayRepository(client)
    feedback=st.session_state.get('play_feedback')
    if feedback and feedback.get('duel_id')==duel_id:
        card=feedback['card'];response=feedback['feedback']
        st.subheader(f"Question {response['index']+1} of 30")
        st.write(card['question'])
        if response['timed_out']:st.warning('Time expired.')
        elif response['correct']:st.success('Correct!')
        else:st.error('That answer was incorrect.')
        for a in card['answers']:
            if a['id']==card['correct_answer_id']:st.success('✓ '+a['text'])
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
            ratings[deck['id']]=st.radio(deck['name'],['up','neutral','down'],index=None,format_func=lambda v:{'up':'👍 Helpful','neutral':'— Neutral','down':'👎 Needs work'}[v],horizontal=True,key='rating_'+duel_id+deck['id'])
        if st.button('Finish round',type='primary',disabled=not all(ratings.values())):
            if play_request(repository,'finish',{'duel_id':duel_id,'ratings':ratings}) is not None:
                st.session_state.play_in_round=False;st.session_state.pop('play_duel',None);st.rerun()
        return
    st.progress(result['index']/30,text=f"Question {result['index']+1} of 30")
    st.caption(f"⏱ {result['seconds']} seconds remaining · Closing this page does not reset the timer.")
    st.subheader(result['question'])
    if result.get('allow_calculator') is True:question_calculator(f'play_{duel_id}_{result["index"]}')
    cols=st.columns(2)
    for i,option in enumerate(result['options']):
        if cols[i%2].button(option['text'],key=f"play_answer_{duel_id}_{result['index']}_{option['id']}",use_container_width=True):
            response=play_request(repository,'answer',{'duel_id':duel_id,'index':result['index'],'answer_id':option['id']})
            if response is not None:
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


STUDY_LEVELS={'new':'New','0':'Needs practice','1':'Building confidence','2':'Getting stronger','3':'Well practised'}


def study_progress_summary(cards):
    counts={k:0 for k in STUDY_LEVELS}
    for c in cards:counts['new' if c.get('level') is None else str(c['level'])]+=1
    colors={'new':'#CBD5E1','0':'#FECACA','1':'#FDBA74','2':'#FDE047','3':'#86EFAC'}
    descriptions={'new':'Not answered yet','0':'Ready to revisit','1':'Learning level 1 of 3','2':'Learning level 2 of 3','3':'Learning level 3 of 3'}
    st.html('<style>'+ (Path(__file__).parent/'assets'/'study-design.css').read_text()+'</style><div class="study-legend">'+''.join(f'<div class="study-level"><span class="study-swatch" style="background:{colors[k]}"></span><span><strong>{STUDY_LEVELS[k]}</strong><small>{descriptions[k]}</small></span><b>{v}</b></div>' for k,v in counts.items())+'</div>')
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
    elif answer is None:draft['cards'][index][field]=st.session_state[key]
    else:draft['cards'][index]['answers'][answer]['text']=st.session_state[key]


def study_editor(client,profile):
    from logic import new_card,validate_card,validate_study_deck
    d=st.session_state.study_draft;revision=st.session_state.get('study_revision',0)
    st.subheader('Edit Study deck')
    st.caption('Study decks are private. A together session shares a fixed copy only with a partner who finishes.')
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
    for label,field in [('Chapter / lecture (optional)','chapter'),('Question','question')]:
        key=prefix+field
        st.text_input(label,value=c.get(field,''),key=key,on_change=study_edit_change,args=(field,key,index))
    st.caption('Use a topic label that does not reveal the answer.')
    for i,a in enumerate(c['answers']):
        key=prefix+a['id'];st.text_input(f'Answer {i+1}',value=a['text'],key=key,on_change=study_edit_change,args=('answers',key,index,i))
    ids=[a['id'] for a in c['answers']];key=prefix+'correct'
    st.radio('Correct answer',ids,index=ids.index(c['correct_answer_id']) if c['correct_answer_id'] in ids else None,format_func=lambda x:f'Answer {ids.index(x)+1}',key=key,on_change=study_edit_change,args=('correct_answer_id',key,index))
    key=prefix+'calculator'
    st.checkbox('Allow calculator for this question',value=c.get('allow_calculator',False),key=key,on_change=study_edit_change,args=('allow_calculator',key,index))
    add,delete=st.columns(2)
    if add.button('Add Study question'):
        try:validate_card(c)
        except ValueError as exc:st.error(str(exc))
        else:
            d['cards'].append(new_card());st.rerun()
    if delete.button('Remove Study question',disabled=len(d['cards'])<=1):
        d['cards'].pop(index);st.rerun()
    st.caption(f"{len(d['cards'])} questions. Changing question content resets its learning level; changing a chapter label does not.")
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
        for i,c in enumerate(deck['cards']):
            level='new' if c.get('level') is None else str(c['level'])
            with st.expander(f"{i+1}. {c.get('chapter') or 'General'} · {STUDY_LEVELS[level]} · {c['question']}"):
                show_deck_cards([c])
                if c.get('note'):st.info('Your private note: '+c['note'])
                for f in c.get('feedback',[]):st.caption('Feedback you sent: '+f)
        return
    data=study_request(client,'list')
    if data is None:return
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
    with st.expander('Feedback on your questions'):
        if not data['feedback']:st.caption('No feedback yet.')
        for f in data['feedback']:
            st.write(f['question']);st.info(f['body']);st.caption(f"From {f['username']} · {f['created_at']}")


def study_round_screen(client,sid):
    r=study_request(client,'round',{'id':sid})
    if r is None:return
    if st.button('Save and leave Study session'):
        st.session_state.pop('study_session',None);st.rerun()
    state=r['state']
    if state in ('question','feedback'):
        st.progress(r['index']/r['total'],text=f"Question {r['index']+1} of {r['total']}")
        if state=='question':
            st.caption(r['part']+' · '+(r.get('chapter') or 'General'))
            if r.get('deadline'):st.caption('Finish by '+r['deadline'])
            st.subheader(r['question'])
            if r.get('allow_calculator') is True:question_calculator(f'study_{sid}_{r["index"]}')
            cols=st.columns(2)
            for i,a in enumerate(r['options']):
                if cols[i%2].button(a['text'],key=f"study_answer_{sid}_{r['index']}_{a['id']}",use_container_width=True):
                    if study_request(client,'answer',{'id':sid,'index':r['index'],'answer_id':a['id']}) is not None:st.rerun()
        else:
            c=r['card'];st.caption(c.get('chapter') or 'General');st.subheader(c['question'])
            if r['correct']:st.success('Correct!')
            else:st.error('Not quite. Review the correct answer below.')
            for a in c['answers']:
                text=a['text']+(' — Your answer' if a['id']==r['answer_id'] else '')
                if a['id']==c['correct_answer_id']:st.success(text+' — Correct answer')
                else:st.write(text)
            study_progress_summary([c])
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
    st.html('<style>'+(Path(__file__).parent/'assets'/'play-modes.css').read_text()+'</style>')
    st.markdown((Path(__file__).parent/'assets'/'study-mode.svg').read_text().replace('\n',''),unsafe_allow_html=True)
    st.header('Study Mode')
    st.caption(st.session_state.get('study_choice','Study alone'))
    if st.session_state.get('study_session'):
        study_round_screen(client,st.session_state.study_session);return
    if st.button('Change study mode',icon=':material/arrow_back:'):
        st.session_state.pop('study_active',None);st.session_state.pop('study_choose',None);st.rerun()
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
        levels=st.multiselect('Learning levels',list(STUDY_LEVELS),default=list(STUDY_LEVELS),format_func=lambda x:STUDY_LEVELS[x])
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
                    friend=st.selectbox('Choose a friend',[f['id'] for f in friends],format_func=lambda x:next(f['username'] for f in friends if f['id']==x))
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
        levels=st.multiselect('Preferred learning levels',list(STUDY_LEVELS),default=list(STUDY_LEVELS),format_func=lambda x:STUDY_LEVELS[x],key='study_together_levels')
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
            st.session_state.study_session=r['id'];st.session_state.pop('study_request_id',None);st.rerun()


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
        st.write('Choose how you want to play.')
        battle,study=st.columns(2)
        with battle:
            with st.container(border=True,key='battle_mode_card'):
                st.markdown((assets/'battle-mode.svg').read_text().replace('\n',''),unsafe_allow_html=True)
                st.subheader('Battle Mode')
                st.caption('Compete, test your knowledge and earn XP.')
                if st.button('Battle Mode',key='choose_battle_mode',use_container_width=True):
                    st.session_state.play_mode_preview='Battle'
                st.caption('Coming soon')
        with study:
            with st.container(border=True,key='study_mode_card'):
                st.markdown((assets/'study-mode.svg').read_text().replace('\n',''),unsafe_allow_html=True)
                st.subheader('Study Mode')
                st.caption('Practise together and focus on learning.')
                study_design()
                if not st.session_state.get('study_choose'):
                    if st.button('Study Mode',key='choose_study_mode',type='primary',use_container_width=True):
                        st.session_state.study_choose=True;st.rerun()
                else:
                    st.caption('How would you like to study?')
                    for col,(label,icon,material) in zip(st.columns(2),[('Study alone','solo',':material/person:'),('Study together','together',':material/group:')]):
                        with col:
                            if st.button(label,key='enter_'+icon,icon=material,use_container_width=True):
                                st.session_state.study_choice=label;st.session_state.study_active=True;st.session_state.pop('study_join',None);st.session_state.pop('study_choose',None);st.rerun()
        selected=st.session_state.get('play_mode_preview')
        if selected=='Battle':
            st.info('Battle Mode is coming soon. Its competitive workflow is not available yet.')
        with st.expander('Current 30-question duels'):
            st.caption('The existing duel format is still available here, including invitations, random search and saved results.')
            play_lobby(client,profile)


def config(key):
    if os.getenv(key):return os.getenv(key)
    try:return st.secrets.get(key,"")
    except FileNotFoundError:return ""
try:
    url=config("SUPABASE_URL");key=config("SUPABASE_PUBLISHABLE_KEY")
except Exception:
    url=key=""
if not url or not key:
    st.info("StudyDuel is waiting for its Supabase connection. Add the project URL and publishable key to .streamlit/secrets.toml.")
    st.stop()
if "auth" not in st.session_state:
    try:
        client=create_client(url,key,options=ClientOptions(auto_refresh_token=False,persist_session=True))
        st.session_state.auth=AuthService(client,app_url=config("APP_URL") or "http://localhost:8501")
    except Exception:
        st.error("Could not connect to StudyDuel. Please try again shortly.")
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
        st.caption("Opening StudyDuel…")
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
                st.session_state.main_page=saved.get("page") if saved.get("page") in ("Decks","Play","Friends","Leaderboard","Study Plan","Profile") else "Profile"
                if isinstance(saved.get("deck_open"),str):st.session_state.deck_open=saved["deck_open"]
            st.session_state.started=True
        else:
            st.session_state.started=True
            st.session_state.notice="Please sign in again to continue. Your saved profile is still here."
    st.rerun()
if auth.user and not auth.verify():
    for k in list(st.session_state):
        if k!="auth": del st.session_state[k]
    st.session_state.browser_loaded=True
    st.session_state.started=True
    st.warning("Your session has ended. Please sign in again.")
browser_bridge("write",{
    "started":bool(st.session_state.get("started") or auth.user),
    "mode":st.session_state.get("account_mode","Sign in"),
    "route":"edit" if st.session_state.get("editing") else "profile",
    "page":st.session_state.get("main_page","Profile"),
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
    st.html(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px"><img src="data:image/png;base64,{logo_data}" alt="StudyDuel flashcard logo" style="width:90px;height:80px;object-fit:cover"><span style="font-size:36px;font-weight:800;letter-spacing:-1.5px;color:var(--sd-text)">Study<span style="color:var(--sd-accent)">Duel</span></span></div>')
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
try: profile=repo.load()
except Exception:
    st.error("We couldn’t load your profile. Please retry; your saved information hasn’t changed.")
    if st.button("Retry"):st.rerun()
    st.stop()
picture=None
if profile:
    try:picture=render_avatar(profile.get("avatar") or DEFAULT_AVATAR) if profile.get("image_mode")=="Avatar" else repo.image(profile.get("image_path"))
    except Exception:pass
brand,avatar_slot,profile_slot=st.columns([5,.65,1.35],vertical_alignment="center")
with brand:
    st.html(f'<div style="display:flex;align-items:center;gap:8px"><img src="data:image/png;base64,{logo_data}" alt="StudyDuel flashcard logo" style="width:64px;height:56px;object-fit:cover"><span style="font-size:30px;font-weight:800;letter-spacing:-1px;color:var(--sd-text)">Study<span style="color:var(--sd-accent)">Duel</span></span></div>')
with avatar_slot:portrait(picture or render_avatar(DEFAULT_AVATAR),44)
with profile_slot:
    if st.button('Profile',use_container_width=True,key='open_profile'):
        navigate('Profile')
if profile:
    tabs=['Decks','Play','Friends','Leaderboard','Study Plan']
    columns=st.columns(len(tabs))
    page=st.session_state.get('main_page','Profile')
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
    if page in ('Leaderboard','Study Plan'):
        st.title(page)
        descriptions={'Play':'Challenge friends to quiz duels using your course decks.','Leaderboard':'See how your study progress compares with other students.','Study Plan':'Organize your study sessions and upcoming goals.'}
        st.write(descriptions[page]);st.info('Coming soon')
        st.stop()
if st.button('Sign out'):
    message=auth.sign_out().message
    for k in list(st.session_state):del st.session_state[k]
    st.session_state.browser_loaded=True;st.session_state.started=True
    st.session_state.notice=message;st.rerun()
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
        st.write(profile["university"])
        degree_labels={"Bachelor's":"Bachelor","Master's":"Master","Doctorate":"Doctorate","Associate":"Associate degree","Diploma / certificate":"Diploma / certificate"}
        degree=degree_labels.get(profile.get("degree"),"")
        field=profile.get("area","")
        study=degree+(" in "+field if degree and field else field)
        if profile.get("graduation_year"):
            study+=(" · " if study else "")+f"Class of {profile['graduation_year']}"
        if study:st.write(study)
        st.caption(" · ".join(profile["languages"]))
        if st.button("Edit profile"):st.session_state.editing=True;st.rerun()
    a,b,c=st.columns(3)
    a.metric("XP",profile.get("xp",0));b.metric("Win streak",profile.get("win_streak",0));c.metric("Friends",len(friend_state["friends"]) if friend_state else "—")
    st.subheader("Your courses")
    st.caption("Only you can see your course selections.")
    for course in profile["courses"]:st.write("📚 "+course)
    if st.session_state.get("pending_invite"):
        st.info("You have a friend invitation. Open Friends to review and accept it.")
    if st.button("Open friends"):
        st.session_state.main_page="Friends";st.rerun()
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
with st.popover(university or "Select your university",use_container_width=True):
    with st.form("university_lookup"):
        university_query=st.text_input("Search universities",placeholder="Type a university name",key="university_query")
        search_clicked=st.form_submit_button("Search")
    if search_clicked:
        try:
            with st.spinner("Searching universities…"):
                st.session_state.university_results=search_universities(university_query)
            st.session_state.university_search_error=None
        except (ValueError,UniversitySearchError) as exc:
            st.session_state.university_search_error=str(exc)
            st.session_state.university_results=[]
    results=st.session_state.get("university_results",[])
    if st.session_state.get("university_search_error"):
        st.warning(st.session_state.university_search_error)
    elif search_clicked and not results:
        st.info("No match found. You can add your university below.")
    for record in results:
        if st.button(record["label"],key="uni_"+record["id"],use_container_width=True):
            st.session_state.chosen_university=record["label"]
            st.rerun()
    with st.expander("University not listed? Add it yourself"):
        custom_university=st.text_input("University name",max_chars=160)
        if st.button("Use this university"):
            if len(custom_university.strip())<2:
                st.error("Enter your university's full name.")
            else:
                st.session_state.chosen_university=" ".join(custom_university.split())
                st.rerun()
degree=st.selectbox("Degree level (optional)",DEGREES,index=DEGREES.index(profile.get("degree","Not specified")))
area=st.text_input("Field of study (optional)",value=profile.get("area",""),placeholder="For example: Finance, Computer Science or Psychology",max_chars=120)
graduation_year=st.number_input("Expected graduation year (optional)",min_value=2000,max_value=2100,value=profile.get("graduation_year"),step=1,placeholder="For example: 2028",help="Your planned graduation year. Private and editable later.")
st.caption("Degree level and field of study are private for now, ready for future matching.")
course_options=list(dict.fromkeys([*CATALOG.get(university,[]),*profile.get("courses",[])]))
courses=st.multiselect("Your courses",course_options,default=profile.get("courses",[]),accept_new_options=True)
st.caption("Type a missing course and press Enter. If you change university, review your courses before saving. Shared university course search comes later.")
languages=st.multiselect("Languages",LANGUAGES,default=profile.get("languages",[]))
st.caption("University and languages are visible to signed-in students. Your courses remain private.")
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
        st.session_state.notice="Your profile is saved."
        st.rerun()
    except ValueError as exc:
        if "username" in str(exc).lower():
            profile_username_error.error(str(exc))
            st.markdown("<style>.st-key-profile_username input{border:2px solid #D84550!important}</style>",unsafe_allow_html=True)
        else:st.error(str(exc))
if profile and st.button("Cancel changes"):
    st.session_state.editing=False
    st.rerun()
