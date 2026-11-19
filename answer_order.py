"""Stable, per-question ordering for multiple-choice answers."""

from hashlib import sha256


def display_options(options, session_id, question_index):
    """Shuffle answer tiles predictably for a session without mutating a card."""
    def order_key(option):
        token=f"{session_id}:{question_index}:{option['id']}".encode()
        return sha256(token).digest()

    return sorted(options,key=order_key)
