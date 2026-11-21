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
JS = (Path(__file__).parent / "assets" / "university-picker.mjs").read_text()
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
