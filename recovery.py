"""Consume the Supabase recovery redirect fragment without logging credentials."""
import streamlit as st

_callback=st.components.v2.component("studyduel_recovery",html="<span></span>",js="""
export default function({setStateValue}) {
    const params=new URLSearchParams(window.location.hash.slice(1));
    if(params.get('type')==='recovery' || params.has('error_code')) {
        const value={type:params.get('type'),access_token:params.get('access_token'),refresh_token:params.get('refresh_token')};
        window.history.replaceState(null,'',window.location.pathname+window.location.search);
        setStateValue('value',value);
    }
}
""")
def recovery_callback():
    result=_callback(key="recovery_redirect",default={"value":None},on_value_change=lambda:None)
    return result.value
