"""Presentation-only round effects: start countdown and streak display.

Everything here is derived from data the round already loaded; nothing
changes scoring, timing or persistence.
"""

MILESTONES={3:'On fire!',5:'Unstoppable!',10:'Legendary!'}


def streak_length(answers):
    """Consecutive correct answers ending at the most recently answered question."""
    items=sorted((a for a in answers if isinstance(a,dict) and isinstance(a.get('index'),int)),key=lambda a:a['index'])
    streak=0
    for answer in items:
        streak=streak+1 if answer.get('correct') else 0
    return streak


def streak_milestone(streak):
    """A short banner text when a streak reaches a celebrated length."""
    return MILESTONES.get(streak)


def countdown_overlay(mode,decorative=False):
    """The 3-2-1-GO! start overlay; decorative overlays hide themselves via CSS."""
    note='Battle starting…' if mode=='battle' else 'Study starting…'
    classes='round-countdown round-countdown-'+mode+(' is-decorative' if decorative else '')
    return ('<div class="'+classes+'" role="status" aria-label="Round starting">'
            '<div class="round-countdown-digits">'
            '<span class="round-digit n3">3</span><span class="round-digit n2">2</span>'
            '<span class="round-digit n1">1</span><span class="round-digit go">GO!</span>'
            '</div><p class="round-countdown-note">'+note+'</p>'
            '<p class="round-countdown-still">Get ready…</p></div>')
