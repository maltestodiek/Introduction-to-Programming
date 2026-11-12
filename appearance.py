"""Custom-brand colours follow Streamlit's native per-browser theme selection."""
import streamlit as st

PALETTES={
    'light':{'text':'#17223B','muted':'#475569','surface':'#FFFFFF','border':'#CDD5E5',
             'accent':'#4338CA','accent-hover':'#312E81','battle-end':'#EEF2FF','study-end':'#ECFDF5',
             'battle-border':'#C7D2FE','study-border':'#A7F3D0','hover':'#E0E7FF',
             'icon-battle':'#E0E7FF','icon-study':'#D1FAE5','badge':'#D9F8EB','badge-text':'#174E3B','shadow':'#4F46E51A'},
    'dark':{'text':'#EEF2FF','muted':'#B4BFD6','surface':'#182237','border':'#384560',
            'accent':'#B8B1FF','accent-hover':'#DDD9FF','battle-end':'#252346','study-end':'#143635',
            'battle-border':'#514B7B','study-border':'#30675B','hover':'#302B53',
            'icon-battle':'#302E50','icon-study':'#163E35','badge':'#163C32','badge-text':'#9DF0CE','shadow':'#00000040'},
}

def theme_variables(mode):
    palette=PALETTES.get(mode,PALETTES['light'])
    fallback=':root{'+''.join(f'--sd-{key}:{value};' for key,value in palette.items())+'}'
    # Native Streamlit containers update color-scheme immediately in the browser.
    # light-dark() follows that scheme without waiting for a Python rerun.
    adaptive=':root{'+''.join(f'--sd-{key}:light-dark({PALETTES["light"][key]},{PALETTES["dark"][key]});' for key in palette)+'}'
    return fallback+'@supports(color:light-dark(white,black)){'+adaptive+'}'

def apply_appearance():
    # Use the reported theme for the fallback; modern browsers switch immediately
    # through native color-scheme. Streamlit owns the per-browser preference.
    mode=st.context.theme.type
    st.html('<style>'+theme_variables(mode)+'</style>')
