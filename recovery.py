"""Read recovery callbacks and carry the PKCE proof between tabs in the same browser."""
import streamlit as st

_callback = st.components.v2.component("uniarena_recovery", html="<span></span>", js="""
export default function({data, setStateValue}) {
    const key = 'uniarena.recovery.pkce.v1';
    if (data.action === 'save') {
        try {
            localStorage.setItem(key, JSON.stringify({verifier: data.verifier, expires: data.expires}));
            setStateValue('value', 'saved');
        } catch (_) {
            setStateValue('value', 'storage_unavailable');
        }
        return;
    }
    if (data.action === 'clear') {
        try {
            const record = JSON.parse(localStorage.getItem(key));
            if (record?.verifier === data.verifier) localStorage.removeItem(key);
        } catch (_) {}
        return;
    }

    // Community Cloud wraps the app. Inspect each accessible URL independently.
    const windows = [window];
    try {
        if (window.top !== window && window.top.location.origin === window.location.origin)
            windows.unshift(window.top);
    } catch (_) {}

    for (const target of windows) {
        const url = new URL(target.location.href);
        const fragment = new URLSearchParams(url.hash.slice(1));
        if (fragment.get('type') === 'recovery' || fragment.has('error_code')) {
            target.history.replaceState(target.history.state, '', url.pathname + url.search);
            setStateValue('value', {type: fragment.get('type'),
                access_token: fragment.get('access_token'), refresh_token: fragment.get('refresh_token')});
            return;
        }
    }

    const urls = windows.map(target => new URL(target.location.href));
    if (data.hasState || urls.some(url => url.searchParams.has('state'))) return;
    const code = data.code || urls.map(url => url.searchParams.get('code')).find(Boolean);
    if (!code) return;
    let verifier = null;
    try {
        const record = JSON.parse(localStorage.getItem(key));
        if (record && record.expires > Date.now()) verifier = record.verifier;
        else localStorage.removeItem(key);
    } catch (_) {}
    setStateValue('value', {type: 'recovery', code, verifier});
}
""")


def recovery_callback():
    result = _callback(data={"action": "read", "code": st.query_params.get("code"),
                             "hasState": "state" in st.query_params},
                       key="recovery_redirect", default={"value": None}, on_value_change=lambda: None)
    return result.value


def store_recovery_proof(action, verifier, expires=None):
    result = _callback(data={"action": action, "verifier": verifier, "expires": expires}, key="recovery_proof_" + action,
                       default={"value": None}, on_value_change=lambda: None)
    return result.value
