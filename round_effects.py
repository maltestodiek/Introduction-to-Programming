"""Presentation-only round effects: start countdown and streak display.

Everything here is derived from data the round already loaded; nothing
changes scoring, timing or persistence.
"""

from pathlib import Path

ASSETS=Path(__file__).parent/'assets'

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


def answered_accuracy(answers):
    """Percent of answered questions that were correct, or None before the first answer."""
    items=[a for a in answers if isinstance(a,dict) and isinstance(a.get('index'),int)]
    if not items:return None
    return round(100*sum(1 for a in items if a.get('correct'))/len(items))


def accuracy_chip(answers):
    """The live accuracy chip for the overview heading; empty before the first answer."""
    accuracy=answered_accuracy(answers)
    if accuracy is None:return ''
    return '<span class="round-acc">'+str(accuracy)+'<small>% correct</small></span>'


def streak_badge(streak):
    """The flame badge for the overview panel; empty below two in a row."""
    if streak<2:return ''
    return '<span class="round-streak" role="status"><span class="flame">🔥</span>'+str(streak)+' in a row</span>'


def combo_markup(streak,pulse=True):
    """A five-segment combo meter filled by the current streak; it glows when full."""
    filled=min(max(streak,0),5)
    segments=''.join('<span class="round-combo-seg on"></span>' if n<filled else '<span class="round-combo-seg"></span>' for n in range(5))
    full=' round-combo-full' if filled>=5 and pulse else ''
    return ('<div class="round-combo'+full+'"><div class="round-combo-label"><span>Combo</span><span>'+str(filled)+' / 5</span></div>'
            '<div class="round-combo-track">'+segments+'</div></div>')


def countdown_overlay(mode,decorative=False):
    """The 3-2-1 start overlay ending on the mode's emblem; decorative overlays hide themselves via CSS."""
    note='Battle starting…' if mode=='battle' else 'Study starting…'
    icon=(ASSETS/('battle-mode.svg' if mode=='battle' else 'study-mode.svg')).read_text()
    classes='round-countdown round-countdown-'+mode+(' is-decorative' if decorative else '')
    return ('<div class="'+classes+'" role="status" aria-label="Round starting">'
            '<div class="round-countdown-digits">'
            '<span class="round-digit n3">3</span><span class="round-digit n2">2</span>'
            '<span class="round-digit n1">1</span><span class="round-digit round-mode-icon">'+icon+'</span>'
            '</div><p class="round-countdown-note">'+note+'</p>'
            '<p class="round-countdown-still">Get ready…</p></div>')
