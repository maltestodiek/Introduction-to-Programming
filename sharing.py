"""User-initiated sharing; no messages are sent by StudyDuel."""
import streamlit as st
from urllib.parse import quote

_share=st.components.v2.component('studyduel_share',html='''<div class="share"><button class="copy">Copy link</button><button class="native">Share…</button><span role="status" aria-live="polite"></span></div>''',css='''.share{display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-family:system-ui;color:#17223B}button{background:#fff;color:#273D9C;border:1px solid #9CAACB;border-radius:9px;padding:10px 16px;cursor:pointer;font:inherit}button:focus-visible{outline:3px solid #3448B8}span{font-size:14px}''',js='''export default function({data,parentElement}) {
 const root=parentElement.querySelector('.share'),status=root.querySelector('[role=status]');
 root.querySelector('.copy').onclick=async()=>{try{await navigator.clipboard.writeText(data.url);status.textContent='Link copied.';}catch(_){status.textContent='Select and copy the link shown below.';}};
 root.querySelector('.native').onclick=async()=>{if(!navigator.share){status.textContent='Use WhatsApp, Email, or Copy link on this browser.';return;}
 try{await navigator.share({title:'Join me on StudyDuel',text:'Accept my friend invitation on StudyDuel.',url:data.url});status.textContent='Share menu closed.';}
 catch(e){status.textContent=e.name==='AbortError'?'Sharing cancelled. Your link still works.':'Use WhatsApp, Email, or Copy link instead.';}};
}''')

def share_invitation(url):
    _share(data={'url':url},key='share_friend_invitation')
    message='Join me on StudyDuel! Sign in and accept my friend invitation: '+url
    a,b=st.columns(2)
    a.link_button('WhatsApp','https://wa.me/?text='+quote(message,safe=''),use_container_width=True)
    b.link_button('Email','mailto:?subject='+quote('Join me on StudyDuel')+'&body='+quote(message,safe=''),use_container_width=True)
    st.code(url,language=None)
    st.caption('Anyone with this link can accept your invitation until it expires or you revoke it. You choose who to share it with.')
