"""Compact Battle XP, Win streak and Friends row shown beside the avatar."""
from pathlib import Path

_file_stamp=Path(__file__).stat().st_mtime  # lets app.py notice when this file changed under a running server
from html import escape

_STYLE=('<style>.sd-profile-stats{display:flex;flex-wrap:wrap;gap:8px 26px;margin:-6px 0 14px;color:var(--sd-text)}'
        '.sd-profile-stat{display:flex;flex-direction:column;line-height:1.25}'
        '.sd-profile-stat strong{font-size:1.35rem;font-weight:700}'
        '.sd-profile-stat span{font-size:.82rem;color:var(--sd-muted)}</style>')


def profile_stats_html(xp,win_streak,friends):
    """The three profile figures as one row; `friends` is None when the list could not be loaded."""
    def stat(label,value,note=''):
        return f'<div class="sd-profile-stat" role="listitem"><strong>{escape(str(value))}</strong><span>{escape(label)}</span>{note}</div>'
    return (_STYLE+'<div class="sd-profile-stats" role="list" aria-label="Profile figures">'
            +stat('Battle XP',xp['battle'])+stat('Win streak',win_streak)+stat('Friends','—' if friends is None else friends)+'</div>')
