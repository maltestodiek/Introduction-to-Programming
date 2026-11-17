# Third feature Manual deck creation

## Why
Students need reviewed, reusable quiz decks before duels can be built.

## What
The user approved the original rules on 11 November 2026: exactly 15 cards, four answers and one correct answer per card, mandatory review, and no user edits/deletions after publication. Build on the existing authenticated Python/Streamlit/Supabase app. This supersedes the old demo-creator/SQLite deck proposal.

Decks navigation shows the student's selected courses. Publishing uses their verified identity, current university and one of their selected courses. Published decks and solutions are readable by authenticated students at that university. Each course lists titles, creators and Not rated. Course names compare case-insensitively. New courses are still selected through Edit profile.

Manual creation starts with one card. Keep a clickable card list, allow any draft card to be edited/deleted, preserve answer identities and order, reject incomplete cards before adding another, and cap at 15. Trim outer whitespace; permit repeated names/questions/answer text. Save Deck enables only with 15 complete cards and valid metadata. Review shows every answer and marked solution. Back to editing invalidates the review, without discarding content. Create Deck revalidates the exact reviewed snapshot and publishes atomically, with retry protection per draft ID. A new draft with the same name is permitted.

Drafts remain in the current session. Private review snapshots are stored in Supabase for authoritative comparison; review alone does not publish a deck. Saved decks survive refresh/restart/deploy. Keep all database access in db.py, business rules in logic.py, screens in app.py.

Show disabled Anki import and AI from lecture slides options, both labeled Coming soon. No uploads, parsing, model calls or external APIs in this feature.

## Out of scope
Duels, grading, ratings, XP, admin deletion, import, AI, and draft recovery after a full restart. The original translated concept remains a faithful historical document, including its old technology proposal; this spec governs implementation.

## Done when
- Valid 15-card review creates no public deck; confirmation creates one complete deck with stable card/answer identities.
- Invalid metadata/cards and 14/16-card decks cannot be published; rejected writes leave existing data unchanged.
- Any card can be edited/deleted; returning from review preserves content and requires review again.
- Confirmation retries never duplicate the deck; a changed draft cannot use an old review.
- Unauthorized users cannot publish as someone else, publish for unselected courses, read another university's decks, or update/delete published content.
- A fresh connection/process reads identical saved content.
- The manual UI works end to end; placeholders are visibly disabled.

Tests cover these outcomes before implementation. Use isolated Postgres-compatible test storage and mocked providers; do not write tests into the production project.
