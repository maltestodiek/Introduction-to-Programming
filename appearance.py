"""Custom-brand colours follow Streamlit's native per-browser theme selection."""
import base64

import streamlit as st

PALETTES={
    'light':{'text':'#17223B','muted':'#475569','surface':'#FFFFFF','border':'#CDD5E5',
             'accent':'#4338CA','accent-hover':'#312E81','battle-end':'#EEF2FF','study-end':'#ECFDF5',
             'battle-border':'#C7D2FE','study-border':'#A7F3D0','hover':'#E0E7FF',
             'avatar':'#F2F3FF','icon-battle':'#E0E7FF','icon-study':'#D1FAE5','badge':'#D9F8EB','badge-text':'#174E3B',
             'battle-button':'#6EE7B7','battle-button-hover':'#34D399','battle-button-text':'#064E3B','shadow':'#4F46E51A',
             'nav-text':'#6D6A90','nav-hover':'#F4F2FC','nav-selected-text':'#4338CA',
             'nav-selected-start':'#EEEAFF','nav-selected-end':'#EFFAF8',},
    'dark':{'text':'#EEF2FF','muted':'#B4BFD6','surface':'#182237','border':'#384560',
            'accent':'#B8B1FF','accent-hover':'#DDD9FF','battle-end':'#252346','study-end':'#143635',
            'battle-border':'#514B7B','study-border':'#30675B','hover':'#302B53',
            'avatar':'#273149','icon-battle':'#302E50','icon-study':'#163E35','badge':'#163C32','badge-text':'#9DF0CE',
            'battle-button':'#5EEAD4','battle-button-hover':'#2DD4BF','battle-button-text':'#042F2E','shadow':'#00000040',
            'nav-text':'#EEF2FF','nav-hover':'#302B53','nav-selected-text':'#FFFFFF',
            'nav-selected-start':'#6042B5','nav-selected-end':'#523598',},
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

PROFILE_BUTTON_AVATAR_SIZE=28  # px; assets/navigation.css sizes the Profile button artwork to match.

def profile_button_avatar_css(image):
    """CSS that paints the user's picture inside the header Profile button."""
    encoded=base64.b64encode(image).decode()
    return '.st-key-open_profile button::before{background-image:url("data:image/png;base64,'+encoded+'")}'
