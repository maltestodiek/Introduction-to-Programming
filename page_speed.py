"""Small reuse helpers so a click does not repeat work whose result has not changed.

See specs/tasks/faster-page-loads.md.
"""
from pathlib import Path

_file_stamp=Path(__file__).stat().st_mtime  # lets app.py notice when this file changed under a running server

import base64
import io

import streamlit as st
from PIL import Image

VERIFY_EVERY=60     # seconds between confirmations of the signed-in user with Supabase
PROFILE_SECONDS=20  # how long a saved profile is reused while browsing


@st.cache_data(show_spinner=False)
def logo_variants(path,modified):
    """Base64 PNG copies of the logo: 'small' for the header and sign-in, 'medium' for the welcome screen."""
    original=Image.open(path).convert('RGBA')
    copies={}
    for name,width in (('small',224),('medium',680)):
        image=original.resize((width,round(original.height*width/original.width)),Image.LANCZOS)
        buffer=io.BytesIO();image.save(buffer,'PNG',optimize=True)
        copies[name]=base64.b64encode(buffer.getvalue()).decode()
    return copies


@st.cache_data(show_spinner=False,max_entries=500)
def thumbnail(data,size):
    """A square PNG copy of a picture at most `size` pixels wide; the original if it cannot be read."""
    try:
        image=Image.open(io.BytesIO(data)).convert('RGBA')
        side=min(image.size);left=(image.width-side)//2;top=(image.height-side)//2
        image=image.crop((left,top,left+side,top+side)).resize((size,size),Image.LANCZOS)
        buffer=io.BytesIO();image.save(buffer,'PNG',optimize=True)
        return buffer.getvalue()
    except Exception:
        return data


@st.cache_data(show_spinner=False,max_entries=500)
def rendered_avatar(settings):
    """The avatar image for a tuple of (key, value) settings; drawn once per distinct look."""
    from logic import render_avatar
    return render_avatar(dict(settings))


def should_verify(now,last):
    """Whether the signed-in user is due to be confirmed with Supabase again."""
    return last is None or not 0<=now-last<VERIFY_EVERY


class ProfileCache:
    """One user's saved profile, reused briefly. Lives in the user's own session, never shared."""
    def __init__(self,seconds=PROFILE_SECONDS):
        self.seconds=seconds;self.clear()

    def clear(self):
        self.user=None;self.at=None;self.profile=None

    def get(self,user,load,now,fresh=False):
        if not fresh and self.profile is not None and self.user==user and self.at is not None and 0<=now-self.at<self.seconds:
            return self.profile
        profile=load()
        if profile is None:self.clear()
        else:self.user,self.at,self.profile=user,now,profile
        return profile
