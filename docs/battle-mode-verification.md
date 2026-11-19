# Battle Mode verification

Approved rules: [Battle Mode specification](../specs/battle-mode.md) and its [implementation task](../specs/tasks/battle-mode-implementation.md).

## Storage and deployment

Apply `supabase/battle-mode-schema.sql`, then `supabase/battle-xp-only.sql`, then `supabase/battle-question-reports.sql`, after the existing Study and AI-generation migrations. They create separate Battle Deck, search, session, round, rating, daily-ranking and question-report tables. They do not modify legacy 30-question rows or Study progress.

All actions use `auth.uid()` inside `battle_action`. Direct table access is revoked. Battle XP is stored in `game_xp`, mirrored as the profile total in `xp`, and is the only XP used by the leaderboard. The follow-up migration removes `creator_xp`; ratings only affect daily Top Deck scoring. Battle session writes never call Study progress, plan, feedback or shared-deck functions.

## Automated checks

- `uv run pytest -q tests/test_battle_rules.py tests/test_deck_ui.py tests/test_play_ui.py`
- `PGLITE_MODULE=/absolute/path/to/pglite/dist/index.js node tests/battle_database.mjs`
- `uv run pytest -q`

The isolated database check covers public consent, owner-only source access, exactly-15 selection, immutable snapshots, daily Top Deck eligibility, ratings that never award XP, and participant-only question reports. It uses fictional PGlite profiles only.

## Manual walkthrough still required

1. Apply the migration in the Supabase SQL editor and sign in with two authorised test accounts from the same university.
2. Create a reviewed Study deck with at least 15 questions, select exactly 15, accept the public-play statement and submit the Battle Deck.
3. Start a Random Deck and a Top Deck Battle, check the 30-second timer, leave/reopen one session, and finish both players’ 15-question round.
4. Check Good, Neutral and Bad ratings; retry one request and confirm exactly one rating, daily Top Deck score update and no XP award.
5. In a completed Battle review, report one question, then retry it and confirm only one report was saved for that participant and question.
6. Confirm the Battle did not create Study progress, a Study-plan entry or Study feedback.
