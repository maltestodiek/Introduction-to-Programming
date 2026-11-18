"""Type-ahead university field: suggestions appear while typing.

Universities already used in UniArena are matched in the browser; the worldwide ROR directory is
searched live from the browser as the student types. Only the typed text is sent to ROR. A name that
is typed but not picked from the suggestions is returned as "typed", so the app can still look it up
on the server and accept it as entered.
"""
from pathlib import Path

_file_stamp=Path(__file__).stat().st_mtime  # lets app.py notice when this file changed under a running server
import streamlit as st

HTML="""
<div class="uni">
  <label class="uni-label" for="uni-input">University</label>
  <input id="uni-input" class="uni-input" type="text" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="uni-list"
         autocomplete="off" spellcheck="false" maxlength="160" placeholder="Type your university">
  <ul id="uni-list" class="uni-list" role="listbox" hidden></ul>
  <div class="uni-status" role="status" aria-live="polite"></div>
</div>
"""
CSS="""
/* Sizes follow Streamlit's own text inputs and select boxes (14px text, 40px high). */
.uni{font-family:inherit;color:var(--st-text-color,#17223B);font-size:.875rem}
.uni-label{display:block;font-size:.875rem;line-height:1.6;min-height:1.5rem;margin-bottom:.25rem}
.uni-input{box-sizing:border-box;width:100%;height:2.5rem;padding:0 .75rem;font-family:inherit;font-size:.875rem;line-height:1.4;color:inherit;background:var(--st-secondary-background-color,#fff);
  border:1px solid var(--st-border-color,#CDD5E5);border-radius:.5rem;outline:none}
.uni-input:focus{border-color:var(--st-primary-color,#4F46E5);box-shadow:0 0 0 1px var(--st-primary-color,#4F46E5)}
.uni-list{list-style:none;margin:.3rem 0 0;padding:.25rem;max-height:17rem;overflow:auto;background:var(--st-secondary-background-color,#fff);
  border:1px solid var(--st-border-color,#CDD5E5);border-radius:.5rem;box-shadow:0 8px 24px #0000001f}
.uni-list li{padding:.45rem .65rem;border-radius:.4rem;cursor:pointer;line-height:1.35;font-size:.875rem}
.uni-list li[aria-selected=true],.uni-list li:hover{background:var(--st-background-color,#EEF2FF)}
.uni-list li.uni-typed{border-top:1px solid var(--st-border-color,#CDD5E5);margin-top:.25rem;padding-top:.6rem;opacity:.9}
.uni-list small{display:block;font-size:.75rem;opacity:.7}
.uni-status{font-size:.75rem;opacity:.75;min-height:1rem;margin-top:.2rem}
"""
JS=r"""
export default function(component){
  const {data,parentElement,setStateValue}=component;
  const input=parentElement.querySelector('.uni-input'),list=parentElement.querySelector('.uni-list'),status=parentElement.querySelector('.uni-status');
  const known=(data.known||[]).filter(n=>typeof n==='string');
  const focused=parentElement.getRootNode().activeElement===input;
  if(!focused){input.value=data.current||'';list.hidden=true;input.setAttribute('aria-expanded','false');}
  let options=[],active=-1,timer=null,request=null,serial=0;
  const clean=t=>t.replace(/\s+/g,' ').trim();
  const close=()=>{list.hidden=true;input.setAttribute('aria-expanded','false');active=-1;};
  const choose=o=>{input.value=o.name;close();status.textContent='';setStateValue('value',{name:o.name,source:o.source});};
  const draw=()=>{
    list.replaceChildren();
    options.forEach((o,i)=>{
      const li=document.createElement('li');li.setAttribute('role','option');li.id='uni-option-'+i;li.setAttribute('aria-selected',i===active?'true':'false');
      if(o.source==='typed'){li.className='uni-typed';li.textContent='Use “'+o.name+'”';const s=document.createElement('small');s.textContent='Not in the list? Keep it as typed.';li.append(s);}
      else{li.textContent=o.name;if(o.source==='known'){const s=document.createElement('small');s.textContent='Already used in UniArena';li.append(s);}}
      li.onmousedown=e=>{e.preventDefault();choose(o);};
      list.append(li);
    });
    list.hidden=options.length===0;input.setAttribute('aria-expanded',String(!list.hidden));
    if(active>=0){input.setAttribute('aria-activedescendant','uni-option-'+active);list.children[active].scrollIntoView({block:'nearest'});}else input.removeAttribute('aria-activedescendant');
  };
  const build=(text,directory)=>{
    const lower=text.toLowerCase(),seen=new Set(),out=[];
    for(const name of known){if(name.toLowerCase().includes(lower)&&!seen.has(name.toLowerCase())){seen.add(name.toLowerCase());out.push({name,source:'known'});}}
    for(const name of directory){if(!seen.has(name.toLowerCase())){seen.add(name.toLowerCase());out.push({name,source:'directory'});}}
    if(!seen.has(lower))out.push({name:text,source:'typed'});
    options=out;active=out.length&&out[0].source!=='typed'?0:-1;draw();
  };
  const search=async text=>{
    const mine=++serial;if(request)request.abort();request=new AbortController();
    build(text,[]);status.textContent='Searching universities…';
    try{
      const escaped=text.replace(/([+\-=><!(){}\[\]^"~*?:\\/|&])/g,'\\$1');
      const response=await fetch('https://api.ror.org/v2/organizations?'+new URLSearchParams({query:escaped,filter:'types:education'}),{headers:{Accept:'application/json'},signal:request.signal});
      if(!response.ok)throw new Error('directory');
      const payload=await response.json();if(mine!==serial)return;
      const names=[];
      for(const item of payload.items||[]){
        if(!(item.types||[]).includes('education')||(item.status||'active')!=='active'||!/^https:\/\/ror\.org\/[a-z0-9]+$/.test(item.id||''))continue;
        const preferred=(item.names||[]).find(n=>(n.types||[]).includes('ror_display'));if(!preferred)continue;
        const country=((item.locations||[]).map(l=>(l.geonames_details||{}).country_name).find(c=>c))||'';
        names.push(country?preferred.value+' — '+country:preferred.value);
      }
      build(text,names);status.textContent=names.length?'':'No directory match. You can keep the name as typed.';
    }catch(e){if(e.name==='AbortError'||mine!==serial)return;build(text,[]);status.textContent='University search is unavailable right now. You can keep the name as typed.';}
  };
  input.oninput=()=>{
    clearTimeout(timer);const text=clean(input.value);
    if(text.length<2){serial++;if(request)request.abort();options=[];draw();status.textContent=text?'Type at least 2 letters.':'';return;}
    build(text,[]);timer=setTimeout(()=>search(text),250);
  };
  input.onfocus=()=>{input.select();};
  input.onkeydown=e=>{
    if(e.key==='ArrowDown'||e.key==='ArrowUp'){if(!options.length)return;e.preventDefault();active=(active+(e.key==='ArrowDown'?1:-1)+options.length)%options.length;draw();}
    else if(e.key==='Enter'){e.preventDefault();const text=clean(input.value);if(active>=0)choose(options[active]);else if(text.length>=2)choose({name:text,source:'typed'});}
    else if(e.key==='Escape'){close();input.value=data.current||'';status.textContent='';}
  };
  input.onblur=()=>{setTimeout(()=>{close();if(clean(input.value)!==clean(data.current||'')){input.value=data.current||'';status.textContent='';}},150);};
  return ()=>{clearTimeout(timer);if(request)request.abort();input.oninput=null;input.onkeydown=null;input.onblur=null;input.onfocus=null;};
}
"""
_picker=st.components.v2.component("uniarena_university_picker",html=HTML,css=CSS,js=JS)


def clean_choice(value,current):
    """The (name, source) a stored component value stands for; anything malformed keeps the current choice."""
    if not isinstance(value,dict) or not isinstance(value.get("name"),str):return current,"saved"
    name=" ".join(value["name"].split())[:160]
    source=value.get("source") if value.get("source") in ("known","directory","typed") else "saved"
    return (name,source) if len(name)>=2 else (current,"saved")


def university_picker(known,current,key="university_picker"):
    """Draw the field and return (name, source); source is "known", "directory", "typed" or "saved"."""
    state=st.session_state.get(key,{})
    stored=state.get("value") if hasattr(state,"get") else None
    _picker(data={"known":list(known or []),"current":current or ""},default={"value":{"name":current or "","source":"saved"}},key=key,on_value_change=lambda:None)
    return clean_choice(stored,current or "")
