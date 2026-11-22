"""Compact Battle XP, Win streak and Friends row shown beside the avatar."""
from pathlib import Path

_file_stamp=Path(__file__).stat().st_mtime  # lets app.py notice when this file changed under a running server
from html import escape

def profile_stats_html(xp,win_streak,friends):
    """The three profile figures as one row; `friends` is None when the list could not be loaded."""
    def stat(label,value,note=''):
        return f'<div class="sd-profile-stat" role="listitem"><strong>{escape(str(value))}</strong><span>{escape(label)}</span>{note}</div>'
    return ('<div class="sd-profile-stats" role="list" aria-label="Profile figures">'
            +stat('Lifetime Battle XP',xp['battle'])+stat('Win streak',win_streak)+stat('Friends','—' if friends is None else friends)+'</div>')
