# Verification workflow

For each task, read its named spec and review the expected outcomes before writing implementation code. List required state, persistent fields, an allowed action, a rejected action and what must survive a full process restart. Keep content separate from per-user progress.

Run `uv run pytest -q` (or `sh run-tests.sh` on the configured Mac). Narrow checks are appropriate for focused changes; broaden them when shared behavior changes. Tests must not weaken, skip or delete accepted expectations merely to pass.

SQL/RLS checks live in `tests/decks_database.mjs`, `tests/play_database.mjs`, `tests/study_database.mjs`, `tests/chat_database.mjs` and `tests/session_friends_database.mjs`. They use a local PGlite engine; set PGLITE_MODULE to its installed module path. SQL scripts under tests/sql are for isolated fixtures only. Never run tests on production students or conversations.

Manually verify the accepted action, rejection without saved-data changes, navigation/resume, and a full stop/start when persistence changes. Check theme/layout changes visually in light and dark mode. Account owners verify real email confirmation/recovery; automated tests must not send real messages.

Record the command, actual result, changed files and any remaining manual limitations in the task/PR. See [Study verification](study-mode-verification.md), [profile scenarios](profile-requirements.md), [restoration checks](launch-and-resume.md), and [current status](implementation-status.md). Older unimplemented test proposals are archived, not current test results.
