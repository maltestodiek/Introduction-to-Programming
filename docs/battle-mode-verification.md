# Battle Mode verification

Approved rules: [Battle Mode specification](../specs/battle-mode.md) and its [implementation task](../specs/tasks/battle-mode-implementation.md).

## Storage and deployment

Apply `supabase/battle-mode-schema.sql`, then `supabase/battle-xp-only.sql`, `supabase/battle-question-reports.sql`, `supabase/battle-deck-availability.sql`, `supabase/battle-search-controls.sql`, `supabase/battle-deck-catalog.sql`, and `supabase/battle-top-decks-immediate.sql`, after the existing Study and AI-generation migrations. They create separate Battle Deck, search, session, round, rating, daily-ranking and question-report tables. They do not modify legacy 30-question rows or Study progress. `battle-deck-catalog.sql` only adds the read-only `battle_deck_catalog()` function that lists same-university Battle Decks for the student's courses on the Decks page, without their questions; `tests/battle_catalog_database.mjs` checks it in isolated PGlite.

All actions use `auth.uid()` inside `battle_action`. Direct table access is revoked. Battle XP is stored in `game_xp`, mirrored as the profile total in `xp`, and is the only XP used by the leaderboard. The follow-up migration removes `creator_xp`; ratings only affect daily Top Deck scoring. Battle session writes never call Study progress, plan, feedback or shared-deck functions.

## Automated checks

- `uv run pytest -q tests/test_battle_rules.py tests/test_deck_ui.py tests/test_play_ui.py`
- `PGLITE_MODULE=/absolute/path/to/pglite/dist/index.js node tests/battle_database.mjs`
- `uv run pytest -q`

The isolated database check covers public consent, owner-only source access, exactly-15 selection, immutable snapshots, daily Top Deck eligibility, pre-match Battle Deck availability, ratings that never award XP, and participant-only question reports. It uses fictional PGlite profiles only.

## Manual walkthrough still required

1. Apply the migration in the Supabase SQL editor and sign in with two authorised test accounts from the same university.
2. Select a course/language without a public Battle Deck and confirm that random matchmaking is disabled with the missing-deck message.
3. Create a reviewed Study deck with at least 15 questions, select exactly 15, accept the public-play statement and submit the Battle Deck.
4. Start a Random Deck and a Top Deck Battle, confirm an unmatched Random Deck request appears under Pending with a live one-hour countdown; use Cancel search, then search again. With two test accounts, create a match and confirm the searching account moves to Ongoing without manually reloading. At expiry confirm the card disappears, check the 30-second timer, then confirm Leave records a loss and the abandoned session cannot be resumed; finish a separate 15-question round with both players.
5. Check Good, Neutral and Bad ratings; retry one request and confirm exactly one rating, daily Top Deck score update and no XP award.
6. In a completed Battle review, report one question, then retry it and confirm only one report was saved for that participant and question.
7. Confirm the Battle did not create Study progress, a Study-plan entry or Study feedback.
