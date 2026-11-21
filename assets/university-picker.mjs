export default function(component){
  const {data,parentElement,setStateValue}=component;
  const input=parentElement.querySelector('.uni-input'),list=parentElement.querySelector('.uni-list'),status=parentElement.querySelector('.uni-status');
  const known=(data.known||[]).filter(n=>typeof n==='string');
  const focused=parentElement.getRootNode().activeElement===input;
  if(!focused){input.value=data.current||'';list.hidden=true;input.setAttribute('aria-expanded','false');}
  let options=[],active=-1,timer=null,request=null,serial=0;
  const cache = input.directoryCache ??= new Map();
  const cancelSearch = () => {
    serial++;
    clearTimeout(timer);
    if (request) request.abort();
  };
  const clean=t=>t.replace(/\s+/g,' ').trim();
  const close=()=>{list.hidden=true;input.setAttribute('aria-expanded','false');active=-1;};
  const choose=o=>{cancelSearch();input.value=o.name;close();status.textContent='';setStateValue('value',{name:o.name,source:o.source});};
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
    const key = text.toLowerCase();
    const display = names => {
      build(text, names);
      status.textContent = names.length ? '' : 'No directory match. You can keep the name as typed.';
    };
    const cached = cache.get(key);
    if (cached && cached.expires > Date.now()) {
      display(cached.names);
      return;
    }
    const mine = serial;
    const controller = new AbortController();
    request = controller;
    const deadline = setTimeout(() => controller.abort(), 8000);
    build(text,[]);status.textContent='Searching universities…';
    try{
      const escaped=text.replace(/([+\-=><!(){}\[\]^"~*?:\\/|&])/g,'\\$1');
      const response=await fetch('https://api.ror.org/v2/organizations?'+new URLSearchParams({query:escaped,filter:'types:education'}),{headers:{Accept:'application/json'},signal:controller.signal});
      if(!response.ok)throw new Error('directory');
      const payload=await response.json();if(mine!==serial)return;
      const names=[];
      for(const item of payload.items||[]){
        if(!(item.types||[]).includes('education')||(item.status||'active')!=='active'||!/^https:\/\/ror\.org\/[a-z0-9]+$/.test(item.id||''))continue;
        const preferred=(item.names||[]).find(n=>(n.types||[]).includes('ror_display'));if(!preferred)continue;
        const country=((item.locations||[]).map(l=>(l.geonames_details||{}).country_name).find(c=>c))||'';
        names.push(country?preferred.value+' — '+country:preferred.value);
      }
      cache.delete(key);
      if (cache.size >= 128) cache.delete(cache.keys().next().value);
      cache.set(key, {names, expires: Date.now() + 600000});
      display(names);
    }catch(e){
      if(mine!==serial)return;
      build(text,[]);
      status.textContent='University search is unavailable right now. You can keep the name as typed.';
    }finally{
      clearTimeout(deadline);
    }
  };
  input.oninput=()=>{
    cancelSearch();const text=clean(input.value);
    if(text.length<2){options=[];draw();status.textContent=text?'Type at least 2 letters.':'';return;}
    build(text,[]);timer=setTimeout(()=>search(text),250);
  };
  input.onfocus=()=>{input.select();};
  input.onkeydown=e=>{
    if(e.key==='ArrowDown'||e.key==='ArrowUp'){if(!options.length)return;e.preventDefault();active=(active+(e.key==='ArrowDown'?1:-1)+options.length)%options.length;draw();}
    else if(e.key==='Enter'){e.preventDefault();const text=clean(input.value);if(active>=0)choose(options[active]);else if(text.length>=2)choose({name:text,source:'typed'});}
    else if(e.key==='Escape'){cancelSearch();close();input.value=data.current||'';status.textContent='';}
  };
  input.onblur=()=>{setTimeout(()=>{close();if(clean(input.value)!==clean(data.current||'')){input.value=data.current||'';status.textContent='';}},150);};
  return ()=>{cancelSearch();input.oninput=null;input.onkeydown=null;input.onblur=null;input.onfocus=null;};
}
