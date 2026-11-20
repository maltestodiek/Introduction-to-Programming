# Unsaved-creation warning

Parent topics: [Deck authoring](../deck-authoring.md) and [Appearance and navigation](../appearance-and-navigation.md).

## Why

Leaving a deck-creation flow silently discarded work in progress: a checked Anki package with AI-read image text, extracted PDF slide texts, or unsaved Study-editor changes disappeared without warning.

## What

Every deck-creation flow — the manual Study editor, the Anki import and the lecture-slides import — confirms before unsaved content is dropped. The Back control opens a centred modal over a dimmed page saying the content is not saved and will be discarded, with **Keep working** and **Leave and discard**. When nothing unsaved exists (no package checked yet, no slides extracted, or the import was just saved), leaving needs no confirmation. The AI-generation page keeps its plain Back control because its drafts are already stored on the server. The modal reuses the Battle leave-confirmation design.

The change is interface only and adds no state or persistence.

## Out of scope

Autosaving drafts, blocking sidebar navigation, or changing what saving and discarding store.

## Done when

1. Allowed: leaving with nothing unsaved returns directly; **Keep working** returns to the untouched flow; **Leave and discard** drops exactly what the old controls dropped.
2. Rejected: a single click on Back with unsaved content never discards it.
3. Restart: saved imports and saved decks are unaffected by discarding; a new sign-in shows them unchanged.
4. All three creation flows show the same centred modal with a message that the contents will not be saved.

Checks: `tests/test_leave_creation.py`, plus a manual look at all three flows.
