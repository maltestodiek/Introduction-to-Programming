import tomllib
from pathlib import Path
from appearance import PALETTES,theme_variables

def luminance(hex_color):
    rgb=[int(hex_color[i:i+2],16)/255 for i in (1,3,5)]
    linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    return sum(a*b for a,b in zip(linear,[.2126,.7152,.0722]))

def contrast(a,b):
    low,high=sorted([luminance(a),luminance(b)])
    return (high+.05)/(low+.05)

def test_custom_text_remains_readable_on_both_card_themes():
    for palette in PALETTES.values():
        for foreground in ('text','muted','accent'):
            for background in ('surface','battle-end','study-end'):
                assert contrast(palette[foreground],palette[background])>=4.5


def test_battle_mode_mint_button_text_remains_readable():
    for palette in PALETTES.values():
        assert contrast(palette['battle-button-text'],palette['battle-button'])>=4.5
        assert contrast(palette['battle-button-text'],palette['battle-button-hover'])>=4.5

def test_battle_feedback_and_friends_actions_have_contrast_in_both_themes():
    for palette in PALETTES.values():
        for status in ('success', 'danger', 'warning'):
            assert contrast(palette[f'{status}-text'], palette[f'{status}-surface']) >= 4.5
        for fill in ('action', 'action-hover'):
            assert contrast('#FFFFFF', palette[fill]) >= 4.5
        assert contrast(palette['muted'], palette['surface-muted']) >= 4.5
        assert contrast(palette['badge-text'], palette['study-end']) >= 4.5


def test_native_controls_have_light_and_dark_configuration():
    config=tomllib.loads((Path(__file__).parents[1]/'.streamlit/config.toml').read_text())['theme']
    for mode in ('light','dark'):
        for surface in ('backgroundColor','secondaryBackgroundColor'):
            assert contrast(config[mode]['textColor'],config[mode][surface])>=4.5

def test_dialogs_inherit_the_reported_theme_from_the_document_root():
    css = theme_variables('dark')
    assert css.startswith(':root{--sd-text:#EEF2FF;')
    assert '.stApp{--sd-text:light-dark(#17223B,#EEF2FF);' in css


def test_unknown_theme_falls_back_to_light_without_injecting_input():
    assert theme_variables('unexpected')==theme_variables('light')


def test_avatar_character_is_opaque_but_backdrop_is_transparent():
    import io
    from PIL import Image
    from logic import render_avatar,DEFAULT_AVATAR
    im=Image.open(io.BytesIO(render_avatar(DEFAULT_AVATAR)))
    assert im.mode=='RGBA'
    assert im.getpixel((0,0))[3]==0
    assert im.getpixel((256,256))[3]==255
