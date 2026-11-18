"""Presentation-safe state for the Study round interface."""


def study_progress_tiles(answers, current_index, total):
    """Return one display state per Study question without exposing answer text."""
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
