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

## Live multiplayer tests

On 21 November 2026, two demo players at the same university used separate browsers on the [public UniArena app](https://uniarena.streamlit.app/). Both selected Corporate Finance in English. Chats, random Battle matchmaking and a complete friend Study Together session passed.

| Screen | How the other player sees a change | What happened in the live test |
| --- | --- | --- |
| Open chat | The conversation checks for new messages every 3 seconds. The inbox and the sidebar unread count check every 15 seconds when active for that view. | A message appeared in the recipient’s open conversation after about 2.2 seconds without either player reloading. The inbox and badge intervals were checked in code only. |
| Battle → Pending | The countdown updates every second. While a search is pending, the app checks the database for a match about every 10 seconds. When the search leaves the queue, the overview reloads automatically. | The first player waited in Pending. About 7 seconds after the second player opted in, the first saw the named opponent in Ongoing and an empty Pending section without clicking. The joining player opened question 1 of 15. The test ended there. |
| Study Together → Waiting for a partner | After answering their own half, the waiting player clicks **Check for a study partner** to fetch the latest state. | The first player answered 10 questions. The friend accepted the invitation with a compatible deck. The first player’s screen stayed on Waiting until they clicked the button, then opened question 11 from the friend’s deck. |
| Study Together → Result | The last finisher sees the result on completion. The player already on the result screen clicks **Refresh session result** to see the partner’s score. | Each player answered the same 20 questions, 10 from each deck, starting with their own. One intentionally wrong answer produced **Loss, 19/20** for the last finisher and **Win, 20/20** for the first finisher after clicking refresh. Both screens also showed the other player’s score. |

### How the two browsers stay in sync

Supabase PostgreSQL stores messages, matchmaking searches, sessions, answers and scores. Each browser has its own Streamlit session. On the screens above, a timed Streamlit fragment or a button click reads the saved state again. The measured delays show one two-player run. Network time and the point in the polling cycle can change the delay. [Refresh logic in the app](../app.py)

The database also decides what happens when actions overlap. Resending the same chat request returns the saved message once. Battle processes competing searches in sequence and removes a matched search from the queue, so another player cannot claim it. Study likewise processes partner claims in sequence. These rules were checked in the implementation. The live run did not simulate simultaneous claims, a class-sized load or random Study Together matching. [Chat rules](../supabase/chat-schema.sql) · [Battle rules](../supabase/battle-mode-schema.sql) · [Study rules](../supabase/study-schema.sql)
