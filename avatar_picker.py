"""Accessible swipe carousel with immediate previews and persisted widget state."""
import base64
from functools import lru_cache
import streamlit as st
from logic import DEFAULT_AVATAR, OPTIONS, render_avatar

LABELS={"skin":"Skin","hair":"Hair","hair_color":"Hair color","clothing":"Clothes","accessory":"Accessories"}
SKIN_LABELS={"Light":"Light","Medium":"Tanned","Deep":"Coloured"}
HTML="""
<div class="avatar-editor">
  <div class="categories" role="tablist" aria-label="Avatar category"></div>
  <div class="stage" tabindex="0" role="group" aria-label="Avatar preview. Swipe left or right, or use arrow keys to change the selected design.">
    <div class="halo"></div><img class="portrait" alt="Your customized avatar" draggable="false">
    <button class="previous" aria-label="Previous design">‹</button>
    <button class="next" aria-label="Next design">›</button>
  </div>
  <div class="selection" aria-live="polite"><strong></strong><span></span></div>
  <div class="dots" aria-label="Design options"></div>
  <p>Swipe the character, use the arrows, or pick a dot.</p>
</div>
"""
CSS="""
.avatar-editor{font-family:system-ui,sans-serif;border:1px solid #e2e5f4;border-radius:24px;background:#fff;padding:18px;color:#242844;max-width:600px;margin:auto}
.categories{display:flex;gap:6px;overflow:auto;padding-bottom:12px;scrollbar-width:thin}
button{font:inherit;cursor:pointer;border:0}
.categories button{background:#f0f2fb;white-space:nowrap;border-radius:20px;padding:9px 14px;font-size:14px;color:#444967;flex-shrink:0}
.categories button[aria-selected=true]{background:#4F46E5;color:white}
.stage{position:relative;display:flex;justify-content:center;align-items:center;height:290px;touch-action:pan-y;user-select:none;outline-offset:3px}
.halo{position:absolute;width:235px;height:235px;border-radius:50%;background:#eef0ff}
.portrait{position:relative;width:240px;height:240px;object-fit:contain;border-radius:50%;pointer-events:none;transition:transform .16s}
.previous,.next{position:absolute;top:120px;width:44px;height:44px;border-radius:50%;background:#eef0fb;color:#424fae;font-size:32px;line-height:36px;box-shadow:0 2px 8px #3331}
.previous{left:0}.next{right:0}
.selection{text-align:center;min-height:47px}.selection strong{display:block;font-size:20px}.selection span{display:block;font-size:12px;color:#535D75;margin-top:5px}
.dots{display:flex;justify-content:center;gap:7px;flex-wrap:wrap;margin:14px 0}
.dots button{width:12px;height:12px;border-radius:50%;background:#8993B5;padding:0}
.dots button[aria-current=true]{background:#4F46E5;transform:scale(1.25)}
p{text-align:center;font-size:12px;color:#535D75;margin-bottom:2px}
button:focus-visible{outline:3px solid #acb6ff;outline-offset:3px}
@media(max-width:400px){.stage{height:260px}.portrait{width:210px;height:210px}.halo{width:210px;height:210px}.previous,.next{top:110px}}
@media(prefers-reduced-motion:reduce){.portrait{transition:none}}
"""
JS="""
export default function(component) {
  const {data,parentElement,setStateValue}=component;
  const root=parentElement.querySelector('.avatar-editor');
  const image=root.querySelector('.portrait'), stage=root.querySelector('.stage');
  let settings={...data.current}, category=data.category || 'hair';
  const categories=root.querySelector('.categories');
  const dots=root.querySelector('.dots');
  const label=(field,value)=>field==='skin'?(data.skinLabels[value]||value):value;
  function draw() {
    categories.replaceChildren();
    for(const [key,label] of Object.entries(data.labels)){
      const b=document.createElement('button');
      b.textContent=label;b.role='tab';b.setAttribute('aria-selected',String(key===category));
      b.onclick=()=>{category=key;draw();setStateValue('value',{...settings,_category:category});};
      categories.appendChild(b);
    }
    const choices=data.options[category], index=choices.indexOf(settings[category]);
    root.querySelector('.selection strong').textContent=label(category,settings[category]);
    root.querySelector('.selection span').textContent=data.labels[category]+' · '+(index+1)+' / '+choices.length;
    image.src=data.previews[category][index];
    image.alt='Avatar: '+Object.entries(settings).map(([key,value])=>label(key,value)).join(', ');
    dots.replaceChildren();
    choices.forEach((option,i)=>{
      const b=document.createElement('button');b.setAttribute('aria-label',label(category,option));
      b.setAttribute('aria-current',String(i===index));b.onclick=()=>choose(i);dots.appendChild(b);
    });
  }
  function choose(index){
    const choices=data.options[category];
    settings[category]=choices[(index+choices.length)%choices.length];
    draw();
    image.animate([{transform:'translateX(12px)',opacity:.7},{transform:'translateX(0)',opacity:1}],{duration:140});
    setStateValue('value',{...settings,_category:category});
  }
  function move(direction){choose(data.options[category].indexOf(settings[category])+direction);}
  root.querySelector('.previous').onclick=()=>move(-1);
  root.querySelector('.next').onclick=()=>move(1);
  stage.onkeydown=e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();move(e.key==='ArrowRight'?1:-1);}};
  let start=null;
  stage.onpointerdown=e=>{if(e.target.closest('button'))return;start={x:e.clientX,y:e.clientY};stage.setPointerCapture(e.pointerId);};
  stage.onpointerup=e=>{
    if(!start)return;
    const dx=e.clientX-start.x,dy=e.clientY-start.y;start=null;
    if(Math.abs(dx)>35 && Math.abs(dx)>Math.abs(dy))move(dx<0?1:-1);
  };
  stage.onpointercancel=()=>{start=null;};
  draw();
  return ()=>{stage.onpointerdown=null;stage.onpointerup=null;stage.onpointercancel=null;stage.onkeydown=null;};
}
"""
_picker=st.components.v2.component("studyduel_avatar_swipe",html=HTML,css=CSS,js=JS)

def clean_selection(value,default):
    return {key:value.get(key,default[key]) if value.get(key,default[key]) in choices else default[key]
            for key,choices in OPTIONS.items()}

@lru_cache(maxsize=1500)
def _cached_avatar(settings,render_version):
    return "data:image/png;base64,"+base64.b64encode(render_avatar(dict(settings))).decode()

def avatar_data_url(settings,render_version=2):
    return _cached_avatar(tuple(sorted(settings.items())),render_version)

def avatar_picker(default=None,key="avatar_carousel"):
    default=default or DEFAULT_AVATAR
    state=st.session_state.get(key,{})
    value=state.get("value",default) or default
    current=clean_selection(value,default)
    category=value.get("_category","hair")
    if category not in OPTIONS:category="hair"
    previews={field:[avatar_data_url(dict(current,**{field:choice}),render_version=2) for choice in choices]
              for field,choices in OPTIONS.items()}
    _picker(data={"current":current,"category":category,"options":OPTIONS,"labels":LABELS,"skinLabels":SKIN_LABELS,"previews":previews},
            default={"value":dict(current,_category=category)},key=key,on_value_change=lambda:None)
    return current
