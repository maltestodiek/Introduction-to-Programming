# Study Mode verification

Approved rules: specs/study-mode.md. This supersedes the Study portion of specs/fifth-feature-battle-and-study-modes.md; that document's future competitive Battle design remains unimplemented.

## Storage and deployment
Apply supabase/study-schema.sql once after play-schema.sql. It creates private Study tables and authenticated study_action operations, plus a trigger that records future legacy duel answers in the same learning progress. The migration does not delete or rewrite existing decks, users, duels or XP. New Study decks are private; legacy published decks retain their existing university visibility. Editable Study copies do not change the legacy originals. All production storage is Supabase PostgreSQL, not local files or browser memory. No additional service, AI API or credentials are needed.

A user/session is derived from auth.uid(), never a submitted user ID. All raw Study tables have RLS and revoked client privileges. A short shared transaction lock serializes claims and progress writes. Failed operations roll back their writes. Session request IDs, answer keys, reviews and earned-copy uniqueness protect retries.

Do not reset production tables for tests. Automated database tests create and remove their own temporary PGlite database with fictional users. The optional TEST_STUDY_MIGRATION=1 switch runs the existing Play database tests with Study installed, without changing their expectations.

## Checks
- `sh run-tests.sh`: Python rules, repositories, and Streamlit screens.
- With Node and @electric-sql/pglite installed in a separate test environment: `PGLITE_MODULE=/absolute/path/to/pglite/dist/index.js node tests/study_database.mjs`.
- `TEST_STUDY_MIGRATION=1 PGLITE_MODULE=/absolute/path/to/pglite/dist/index.js node tests/play_database.mjs`.
- Database tests never use the real Supabase URL, users or keys. They cover permissions, snapshots, deadlines, score visibility, answer retry protection, filtering, 100-question eligibility, colour transitions, private notes, author feedback, integration with existing duels and a fresh-process restart.

## Manual walkthrough
1. Decks → Study decks & progress → Create Study deck. Add complete questions and optional chapter names. Review, then confirm saving. A missing answer must keep the draft and show an error.
2. Play → Study Mode → Study alone. Select the deck, chapter(s), any combination of learning levels, and a question count. Too many questions disables Start. All matching questions is also available.
3. Answer. Feedback appears immediately; the answer cannot be changed. Save a private note separately from sending feedback. Next question advances explicitly.
4. Leave the session, stop Streamlit fully, start again, sign in and reopen Your saved study sessions. The answer, note and learning level must persist. Decks → Study decks & progress → View progress and questions shows the same saved progress.
5. With two consenting test accounts, select Study together, same course/language and size. A random search is invisible until the first player completes their own half. No player receives an unsolicited invitation. The second opted-in completed half causes matching. Open sessions instead reserve the selected partner immediately while the joining player answers their own half.
6. Friend mode: sender completes their own half; recipient accepts with a compatible deck or declines. No partner action is simulated on production accounts.
7. Complete one player's entire session. Only that player receives the partner's entire snapshotted deck in Shared with me. Complete the other player to show scores and win/draw/loss. Neither XP nor streak changes. A received copy stays unchanged after its author edits the original.
8. Deadline cases are tested with an isolated database clock adjustment, never by modifying real users' deadlines: unmatched search expires after 24 hours; a matched incomplete player cannot answer after 24 hours. Completed practice and notes remain saved.

## Verification record — 12 November 2026
120 Python checks passed. 14 isolated Study database checks passed, including a separate-process reload. The Supabase migration was applied successfully through the project's SQL editor. Local browser verification uses a separate persisted test database and fictional profile; it is not evidence of a real two-account production duel. No production invitations or author feedback were sent by the agent.

The 21 existing Play database checks also passed with the Study migration installed. Manual browser verification confirmed immediate feedback and the orange level, then stopped both local app and test-database processes. After restarting both, the saved session reopened on the same locked feedback screen and its private note was intact.
