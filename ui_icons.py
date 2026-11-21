"""Outline icons for UI drawn with HTML; widgets use Streamlit's Material icons."""

from urllib.parse import quote

OUTLINES = {
    "swords": '<path d="M3 3h4l12 12-4 4L3 7V3Zm11 4 3-4h4v4l-4 4M3 21l3-3m-2-3 5 5m-3-3 3-3m9 4 3 3m-1-6-5 5"/>',
    "hourglass": '<path d="M6 3h12M6 21h12M8 3v4l4 5 4-5V3M8 21v-4l4-5 4 5v4"/>',
    "shield": '<path d="M12 22c-4-2-8-5-8-10V5l8-3 8 3v7c0 5-4 8-8 10Z"/>',
    "flag": '<path d="M5 22V3m0 1c5-4 9 4 14 0v12c-5 4-9-4-14 0"/>',
    "trophy": '<path d="M7 3h10v6a5 5 0 0 1-10 0V3Zm0 2H3v2a4 4 0 0 0 4 4m10-6h4v2a4 4 0 0 1-4 4m-5 3v5m-4 2h8m-7-2h6"/>',
    "flame": '<path d="M12 22a7 7 0 0 1-7-7c0-2.5 1.6-5.2 3.8-7 .3 1.7 1.2 2.6 2.2 3 1.6-2.7 1-5.9.4-8C15 5 19 9.2 19 15a7 7 0 0 1-7 7Z"/>',
    "sparkles": '<path d="M10 4l1.7 4.3L16 10l-4.3 1.7L10 16l-1.7-4.3L4 10l4.3-1.7L10 4Zm8 10 1 2.6 2.6 1-2.6 1L18 21l-1-2.4-2.6-1 2.6-1 1-2.6ZM18 3v5m-2.5-2.5h5"/>',
    "copy": '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 4H6a2 2 0 0 0-2 2v10"/>',
    "share": '<path d="M12 15V3m-4 4 4-4 4 4M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6"/>',
    "message": '<path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5c-1.3 0-2.5-.3-3.6-.8L4 21l1.5-4.7a8.5 8.5 0 1 1 15.5-4.8Z"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/>',
    "check": '<path d="m5 12 4 4L19 6"/>',
    "close": '<path d="m6 6 12 12M18 6 6 18"/>',
    "add": '<path d="M12 5v14M5 12h14"/>',
    "file": '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-6-6Zm0 0v6h6m-12 4h8m-8 4h8"/>',
}


def inline_icon(name):
    """Draw a decorative icon that inherits its surrounding text color."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        + OUTLINES[name] + '</svg>'
    )
    mask = 'data:image/svg+xml,' + quote(svg, safe='')
    return (
        '<span class="sd-icon" aria-hidden="true" style="display:inline-block;width:1em;height:1em;'
        'flex:none;vertical-align:middle;background:currentColor;'
        f'mask:url({mask}) center / contain no-repeat"></span>'
    )
