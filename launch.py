"""Welcome UI and per-browser resume state. Passwords are never stored."""
import streamlit as st

_bridge=st.components.v2.component('studyduel_resume',html='<span></span>',js="""
export default function({data,setStateValue}) {
  const key='studyduel.resume.v1';
  try {
    if(data.action==='read') {
      let value={};
      try {value=JSON.parse(localStorage.getItem(key)||'{}')||{};} catch (_) {}
      setStateValue('value',value);
    } else {
      localStorage.setItem(key,JSON.stringify(data.value));
    }
  } catch (_) {
    if(data.action==='read') setStateValue('value',{storageUnavailable:true});
  }
}
""")

def browser_bridge(action,value=None):
    result=_bridge(data={'action':action,'value':value},key='browser_resume',default={'value':None},on_value_change=lambda:None)
    return result.value


def welcome(logo):
    st.html(f'''<style>
    .welcome{{text-align:center;padding:30px 16px 8px;color:#17223B}}
    .welcome-mark{{width:min(320px,70vw);height:220px;object-fit:cover;animation:duel-arrive .8s ease-out both,duel-float 4s ease-in-out .8s infinite}}
    .welcome h1{{font-size:clamp(44px,8vw,68px);font-weight:850;letter-spacing:-3px;margin:0!important;line-height:1.15}}
    .welcome h1 span{{color:#4F46E5}}
    .welcome p{{font-size:20px;color:#475467;margin:20px auto 14px;max-width:480px}}
    .welcome-tag{{display:inline-block;background:#D9F8EB;color:#174E3B;padding:7px 16px;border-radius:99px;font-size:14px;font-weight:600;letter-spacing:.03em}}
    @keyframes duel-arrive{{from{{opacity:0;transform:translateY(18px) scale(.85) rotate(-7deg)}}to{{opacity:1;transform:translateY(0) scale(1) rotate(0)}}}}
    @keyframes duel-float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-9px)}}}}
    @media(prefers-reduced-motion:reduce){{.welcome-mark{{animation:none}}}}
    </style><section class="welcome" aria-label="Welcome to StudyDuel">
    <span class="welcome-tag">LEARN TOGETHER. LEVEL UP.</span><br>
    <img class="welcome-mark" src="data:image/png;base64,{logo}" alt="StudyDuel flashcard logo">
    <h1>Study<span>Duel</span></h1><p>A little competition.<br>A lot of learning.</p>
    </section>''')
    _,middle,_=st.columns([1,2,1])
    with middle:
        start=st.button('Start',type='primary',use_container_width=True)
        st.caption('Create an account or sign in to continue.')
    return start
