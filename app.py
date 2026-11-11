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
from sharing import share_invitation
from logic import normalize_friend_code, invitation_url, invitation_token
from logic import CATALOG, LANGUAGES, DEFAULT_AVATAR, OPTIONS, DEGREES, render_avatar, crop_photo, validate_username

LOGO_PATH=Path(__file__).parent / "assets" / "studyduel-icon.png"
st.set_page_config(page_title="StudyDuel",page_icon=Image.open(LOGO_PATH),layout="centered")
st.markdown("""<style>
.block-container{max-width:940px;padding-top:2.5rem}
h1{letter-spacing:-.04em}div[data-testid="stForm"]{background:#FFFFFF;color:#17223B;border:1px solid #CDD5E5;border-radius:18px;padding:24px}
.stButton>button{border-radius:10px}div[data-testid="stMetric"]{background:#FFFFFF;color:#17223B;border:1px solid #CDD5E5;border-radius:16px;padding:20px;border-top:4px solid #6EE7B7}
</style>""",unsafe_allow_html=True)
logo_data=base64.b64encode(LOGO_PATH.read_bytes()).decode()
st.html(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px"><img src="data:image/png;base64,{logo_data}" alt="StudyDuel flashcard logo" style="width:90px;height:80px;object-fit:cover"><span style="font-size:36px;font-weight:800;letter-spacing:-1.5px;color:#17223B">Study<span style="color:#4F46E5">Duel</span></span></div>')
st.caption("A little competition. A lot of learning.")
# The invitation remains in the URL across signup, email confirmation and login.
if "invite" in st.query_params:
    try:st.session_state.pending_invite=invitation_token(st.query_params["invite"])
    except ValueError:
        st.session_state.pop("pending_invite",None)
        st.warning("This invitation link is invalid. Ask your friend for a new one.")

def portrait(data,size=160):
    encoded=base64.b64encode(data).decode()
    st.html(f'<img src="data:image/png;base64,{encoded}" alt="Profile picture" style="width:{size}px;height:{size}px;max-width:100%;object-fit:cover;border-radius:50%;display:block" />')

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
    st.subheader("Friends")
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
        client=create_client(url,key,options=ClientOptions(auto_refresh_token=True,persist_session=True))
        st.session_state.auth=AuthService(client,app_url=config("APP_URL") or "http://localhost:8501")
    except Exception:
        st.error("Could not connect to StudyDuel. Please try again shortly.")
        st.stop()
auth=st.session_state.auth
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
            st.session_state.notice=result.message
            st.rerun()
        else:st.error(result.message)
    if st.button("Back to sign in"):
        auth.sign_out()
        for state_key in list(st.session_state):del st.session_state[state_key]
        st.rerun()
    st.stop()
if st.session_state.get("recovery_error"):
    st.error(st.session_state.recovery_error)
if auth.user and not auth.verify():
    for k in list(st.session_state):
        if k!="auth": del st.session_state[k]
    st.warning("Your session has ended. Please sign in again.")
notice=st.session_state.pop("notice",None)
if notice: st.success(notice)

if not auth.user:
    if st.session_state.get("pending_invite"):st.info("You have a friend invitation. Sign in or create an account, then accept it after completing your profile.")
    st.title("Your next study win starts here.")
    st.write("Create your student profile. Build your knowledge, then challenge your friends.")
    mode=st.segmented_control("Account",["Sign in","Create account"],default="Sign in",key="account_mode")
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
    st.stop()

for credential_key in ("account_password","account_confirmation"):
    st.session_state.pop(credential_key,None)
repo=ProfileRepository(auth.client,auth.user.id)
head,logout=st.columns([4,1])
with logout:
    if st.button("Sign out",use_container_width=True):
        message=auth.sign_out().message
        for k in list(st.session_state):del st.session_state[k]
        st.session_state.notice=message
        st.rerun()
try: profile=repo.load()
except Exception:
    st.error("We couldn’t load your profile. Please retry; your saved information hasn’t changed.")
    if st.button("Retry"):st.rerun()
    st.stop()
editing=not profile or st.session_state.get("editing",False)
if not editing:
    friends=FriendsRepository(auth.client)
    try:friend_state=friends.action("list")
    except ValueError as exc:
        friend_state=None
        st.warning(str(exc))
    picture=None
    try:picture=render_avatar(profile.get("avatar") or DEFAULT_AVATAR) if profile.get("image_mode")=="Avatar" else repo.image(profile.get("image_path"))
    except Exception:pass
    left,right=st.columns([1,3])
    with left:portrait(picture or render_avatar(DEFAULT_AVATAR),176)
    with right:
        code_label=("#"+friend_state["code"]) if friend_state else ""
        st.html(f'<h1 style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin:0 0 16px;color:#17223B"><span>{escape(profile["username"])}</span><span aria-label="Your friend code" style="font-size:16px;font-weight:400;letter-spacing:.03em;color:#667085">{escape(code_label)}</span></h1>')
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
    if friend_state:friends_screen(friends,repo,friend_state)
    elif st.button("Retry friends"):st.rerun()
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
