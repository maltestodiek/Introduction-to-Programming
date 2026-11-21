# Verification workflow

For each task, read its named spec and review the expected outcomes before writing implementation code. List required state, persistent fields, an allowed action, a rejected action and what must survive a full process restart. Keep content separate from per-user progress.

Run `uv run pytest -q` (or `sh run-tests.sh` on the configured Mac). Narrow checks are appropriate for focused changes; broaden them when shared behavior changes. Tests must not weaken, skip or delete accepted expectations merely to pass.

SQL/RLS checks live in `tests/decks_database.mjs`, `tests/play_database.mjs`, `tests/study_database.mjs`, `tests/chat_database.mjs` and `tests/session_friends_database.mjs`. They use a local PGlite engine; set PGLITE_MODULE to its installed module path. SQL scripts under tests/sql are for isolated fixtures only. Never run tests on production students or conversations.

Manually verify the accepted action, rejection without saved-data changes, navigation/resume, and a full stop/start when persistence changes. Check theme/layout changes visually in light and dark mode. Account owners verify real email confirmation/recovery; automated tests must not send real messages.

Record the command, actual result, changed files and any remaining manual limitations in the task/PR. See [Study verification](study-mode-verification.md), [profile scenarios](profile-requirements.md), [restoration checks](launch-and-resume.md), and [current status](implementation-status.md). Older unimplemented test proposals are archived, not current test results.

## Live account tests

All four checks passed on 21 November 2026 in Chrome on the [public UniArena app](https://uniarena.streamlit.app/). The account owner handled the email links and entered the new password.

1. **Email verification.** The owner received the signup email and clicked its confirmation link. Supabase Auth recorded the confirmation. The owner then signed in and reached profile setup.
2. **Sign-in before verification.** A separate demo account was registered. With its confirmation link still unopened, sign-in with the signup credentials showed “Unable to sign in. Check your credentials, confirm your email, or try again shortly.” UniArena stayed on the sign-in screen. Supabase Auth showed a confirmation email had been sent and both the confirmation and last-sign-in timestamps were empty.
3. **Password reset.** After the recovery fix was deployed, a fresh reset email was requested through **Forgot password?**. The owner opened the newest link in the same Chrome profile, saw **Choose a new password**, and reported signing in after updating the password. The signed-in app and its Profile controls were then observed. [Recovery fix (PR #96)](https://github.com/maltestodiek/Introduction-to-Programming/pull/96)
4. **Sign-out survives refresh.** On a completed profile, selecting **Profile → Sign out** showed “You are signed out.” Reloading that same tab returned to **Sign in**. The Profile button was absent after reload.

The sign-out check covers a completed profile. During initial profile setup, the public app had no **Sign out** button.
