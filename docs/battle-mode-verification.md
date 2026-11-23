# Battle Mode verification

Approved rules: [Battle Mode specification](../specs/battle-mode.md) and its [implementation task](../specs/tasks/battle-mode-implementation.md).

## Storage and deployment

Apply `supabase/battle-mode-schema.sql`, then `supabase/battle-xp-only.sql`, `supabase/battle-question-reports.sql`, `supabase/battle-deck-availability.sql`, `supabase/battle-search-controls.sql`, `supabase/battle-deck-catalog.sql`, `supabase/battle-top-decks-immediate.sql`, and `supabase/battle-top-decks-lifetime-ranking.sql`, after the existing Study and AI-generation migrations. Install the subsequent versioned migration `20261121220000_async_battles.sql` for asynchronous Battle starts and deadlines, followed by `20261122010000_battle_leave_loss.sql` for confirmed forfeits, `20261123090000_battle_search_per_course.sql` for one search per normalized course, and `20261123100000_reject_duplicate_course_battle_search.sql` to reject a second start for that course. They create separate Battle Deck, search, session, round, rating, daily-ranking and question-report tables. They do not modify legacy 30-question rows or Study progress. `battle-deck-catalog.sql` adds the read-only `battle_deck_catalog()` function for same-university Battle Decks without exposing their questions; `tests/battle_catalog_database.mjs` checks it in isolated PGlite.

All actions use `auth.uid()` inside `battle_action`. Direct table access is revoked. Battle XP is stored in `game_xp`, mirrored as the profile total in `xp`, and is the only XP used by the leaderboard. The follow-up migration removes `creator_xp`; ratings only affect lifetime Top Deck scoring. Battle session writes never call Study progress, plan, feedback or shared-deck functions.

## Automated checks

- `uv run pytest -q tests/test_battle_rules.py tests/test_deck_ui.py tests/test_play_ui.py`
- `PGLITE_MODULE=/absolute/path/to/pglite/dist/index.js node tests/battle_database.mjs`
- `uv run pytest -q`

The isolated database check covers public consent, owner-only source access, exactly-15 selection, immutable snapshots, lifetime Top Deck eligibility, pre-match Battle Deck availability, ratings that never award XP, and participant-only question reports. It uses fictional PGlite profiles only.

## Manual walkthrough still required

1. Apply the migration in the Supabase SQL editor and sign in with two authorised test accounts from the same university.
2. Select a course/language without a public Battle Deck and confirm that random matchmaking is disabled with the missing-deck message.
3. Create a reviewed Study deck with at least 15 questions, select exactly 15, accept the public-play statement and submit the Battle Deck.
4. Start a random Battle alone. Choose Leave Battle and then Keep fighting. Confirm Leave and lose on the second attempt and check that Recent results shows one loss after restarting. Repeat with a matched opponent and verify the opponent wins. In a fresh Battle, finish all 15 questions before matching and check that it stays in Active battles. Have a compatible second account join and check that both see the same deck. Check Recent results and both XP changes once the outcome is known. The isolated database test advances the deadlines to check the unmatched one-hour and 48-hour expiry and a matched timeout without waiting in real time.
5. Check Good, Neutral and Bad ratings; retry one request and confirm exactly one rating, lifetime Top Deck score update and no XP award.
6. In a completed Battle review, report one question, then retry it and confirm only one report was saved for that participant and question.
7. Confirm the Battle did not create Study progress, a Study-plan entry or Study feedback.
