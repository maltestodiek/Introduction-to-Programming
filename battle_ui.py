"""Presentation-safe state for the Battle round interface."""


def battle_progress_tiles(answers, current_index, total=15):
    """Return one display state per Battle question without exposing answer text."""
    by_index={item.get('index'):item for item in answers if isinstance(item,dict) and isinstance(item.get('index'),int)}
    tiles=[]
    for index in range(total):
        answer=by_index.get(index)
        if answer is not None:
            state='correct' if answer.get('correct') else 'incorrect'
        elif index==current_index:
            state='current'
        else:
            state='open'
        tiles.append({'number':index+1,'state':state})
    return tiles


def timer_fraction(seconds, limit=30):
    """Keep the visible timer within its server-owned 30-second bounds."""
    return max(0.0,min(1.0,float(seconds)/limit))


def timer_tick_fractions(seconds, limit=30):
    """Return the current and next server-tick widths for a smooth countdown."""
    return timer_fraction(seconds,limit),timer_fraction(seconds-1,limit)
