"""Presentation-only round effects: start countdown and streak display.

Everything here is derived from data the round already loaded; nothing
changes scoring, timing or persistence.
"""

from pathlib import Path

from ui_icons import inline_icon

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
    return f'<span class="round-streak" role="status">{inline_icon("flame")}{streak} in a row</span>'


def combo_markup(streak,pulse=True):
    """A five-segment combo meter filled by the current streak; it glows when full."""
    filled=min(max(streak,0),5)
    segments=''.join('<span class="round-combo-seg on"></span>' if n<filled else '<span class="round-combo-seg"></span>' for n in range(5))
    full=' round-combo-full' if filled>=5 and pulse else ''
    return ('<div class="round-combo'+full+'"><div class="round-combo-label"><span>Combo</span><span>'+str(filled)+' / 5</span></div>'
            '<div class="round-combo-track">'+segments+'</div></div>')


# Durations in milliseconds keep the animation and first question in sync.
INTRO_BEATS = (('3', 1000), ('2', 1000), ('1', 1000), ('Best of Luck!', 1430), ('Go!', 770))
INTRO_SECONDS = sum(duration for _, duration in INTRO_BEATS) / 1000


def countdown_overlay(mode):
    """Main-panel intro. Only the decorative spans animate under the status label."""
    words, marks = [], []
    delay = 0
    for word, duration in INTRO_BEATS:
        style = {'Go!': 'go', 'Best of Luck!': 'wish'}.get(word, '')
        words.append(f'<span class="beat {style}" style="--delay:{delay}ms;--duration:{duration}ms">{word}</span>')
        marks.append(f'<i style="--delay:{delay}ms"></i>')
        delay += duration
    rays = ''.join(
        f'<i class="streak" style="--ray:{i * 360 / 26:.2f}deg;--delay:-{(i * 19) % 100 / 70:.2f}s"></i>'
        for i in range(26)
    )
    css = (ASSETS/'session-intro.css').read_text()
    return (
        f'<style>{css}</style><div class="ua-intro {mode}" role="status" aria-label="{mode.title()} session starting">'
        f'<div class="orb" aria-hidden="true"><i class="wave"></i></div>{rays}'
        f'<span class="mode">{mode.title()} Mode</span>'
        f'<div aria-hidden="true" style="display:contents">{"".join(words)}</div>'
        f'<div class="dots" aria-hidden="true">{"".join(marks)}</div></div>'
    )
