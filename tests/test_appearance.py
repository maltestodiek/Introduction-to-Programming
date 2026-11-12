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

def test_native_controls_have_light_and_dark_configuration():
    config=tomllib.loads((Path(__file__).parents[1]/'.streamlit/config.toml').read_text())['theme']
    for mode in ('light','dark'):
        for surface in ('backgroundColor','secondaryBackgroundColor'):
            assert contrast(config[mode]['textColor'],config[mode][surface])>=4.5

def test_unknown_theme_falls_back_to_light_without_injecting_input():
    assert theme_variables('unexpected')==theme_variables('light')
