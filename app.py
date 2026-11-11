"""StudyDuel authentication and profile setup."""
import os
import streamlit as st
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions as ClientOptions
from avatar_picker import avatar_picker
from universities import search_universities, UniversitySearchError
from auth import AuthService
from recovery import recovery_callback
from db import ProfileRepository
from logic import CATALOG, LANGUAGES, DEFAULT_AVATAR, OPTIONS, DEGREES, render_avatar, crop_photo, validate_username

st.set_page_config(page_title="StudyDuel",page_icon="✦",layout="centered")
st.markdown("""<style>
.block-container{max-width:940px;padding-top:2.5rem}
h1{letter-spacing:-.04em}div[data-testid="stForm"]{background:white;border-radius:18px;padding:24px}
.stButton>button{border-radius:10px}div[data-testid="stMetric"]{background:white;border:1px solid #E6E8F2;border-radius:16px;padding:20px}
</style>""",unsafe_allow_html=True)
st.markdown("### ✦ StudyDuel")
st.caption("A little competition. A lot of learning.")
def config(key):
    return os.getenv(key) or st.secrets.get(key,"")
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
            result=auth.sign_up(email,password,confirmation,username)
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
    picture=None
    try:picture=render_avatar(profile.get("avatar") or DEFAULT_AVATAR) if profile.get("image_mode")=="Avatar" else repo.image(profile.get("image_path"))
    except Exception:pass
    left,right=st.columns([1,3])
    with left:st.image(picture or render_avatar(DEFAULT_AVATAR),width=160)
    with right:
        st.title(profile["username"])
        st.write(profile["university"])
        st.caption(" · ".join(profile["languages"]))
        if st.button("Edit profile"):st.session_state.editing=True;st.rerun()
    a,b,c=st.columns(3)
    a.metric("XP",profile.get("xp",0));b.metric("Win streak",profile.get("win_streak",0));c.metric("Friends","0")
    st.subheader("Your courses")
    st.caption("Only you can see your course selections.")
    for course in profile["courses"]:st.write("📚 "+course)
    st.subheader("Your studies")
    st.write(profile.get("degree","Not specified"))
    if profile.get("area"): st.write(profile["area"])
    st.caption("Your degree level and field of study are private.")
    st.subheader("Friends")
    st.info("Your friends list is empty. Friendships and duels are coming in a later feature.")
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
        repo.save(dict(username=name,university=university,courses=courses,languages=languages,avatar=avatar,degree=degree,area=area),
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
