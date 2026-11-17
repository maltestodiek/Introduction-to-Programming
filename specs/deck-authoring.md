# Deck authoring, subsections and question tools

## Why
Students need reviewed course material that can be reused for solo and shared study.

## What
The main Create New Deck action creates a private, editable Study deck with one to 100 questions. Each question has four answers and exactly one correct answer. Select a course and language, name the deck, and type or reuse subsection/lecture names. New questions inherit the current subsection. Chapter labels must not reveal solutions.

Require review before saving. Retain drafts when returning to editing; validate the exact reviewed content before publication/save. Revision checks prevent overwriting concurrent changes. Changed question content creates a new learning-progress identity; chapter-only or calculator-permission changes do not. Supabase stores saved decks; unsaved drafts are not guaranteed to survive a full browser reload.

Full-deck copies earned through Study Together are fixed snapshots: later author edits do not change received copies. The original 15-question published editor remains under Classic 30-question duels and keeps its immutable publication rules; see [classic authoring](../docs/archive/specifications/classic-deck-authoring.md). Those rules do not impose a 15-question limit on new Study decks.

Basic text-only Anki import is implemented under its dedicated task specification. It stores up to 100 private source cards for a later reviewed question-generation workflow. Cloze and image/media cards are rejected with a clear error. AI generation from lecture slides remains disabled.

### Per-question calculator
Both deck editors offer an unchecked Allow calculator for this question setting. It is a strict boolean saved with question content and shown during review. Old questions default to disabled. Active sessions and received deck copies retain the setting from their immutable snapshot. Changing the permission alone does not reset learning progress.

During an enabled question, offer a Calculator panel on the right on desktop with digits, decimals, addition, subtraction, multiplication, division, brackets, backspace, clear and equals. Keep the expression visible and display the result separately, right-aligned. Use distinct button colours for numbers and functions. Include square roots and integer powers from −12 to 12. Calculations never submit an answer, change progress, or pause a duel timer. Use bounded arithmetic parsing in Python, never eval or an external API. Each session/question has separate calculator state.


## Out of scope
AI generation, Cloze/media Anki parsing, automatic chapter quality checks, scientific/graphing calculator functions and changes to classic published-deck rules.

## Done when
Invalid/incomplete questions cannot be saved; rejected writes preserve saved data. Review confirms exactly the saved questions and solutions. Concurrent stale edits are rejected. Subsequent edits never rewrite a partner's earned copy. Calculator availability follows the saved question snapshot; arithmetic rejects invalid or excessive operations and never submits answers. Saved content survives a full process restart.

Checks: `tests/test_deck_rules.py`, `tests/test_deck_repository.py`, `tests/test_deck_ui.py`, `tests/test_study_rules.py`, `tests/test_study_ui.py`, `tests/test_calculator.py`, `tests/decks_database.mjs`, `tests/study_database.mjs`.
