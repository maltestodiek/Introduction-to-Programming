# Verification workflow

For each task, read its named spec and review the expected outcomes before writing implementation code. List required state, persistent fields, an allowed action, a rejected action and what must survive a full process restart. Keep content separate from per-user progress.

Run `uv run pytest -q` (or `sh run-tests.sh` on the configured Mac). Narrow checks are appropriate for focused changes; broaden them when shared behavior changes. Tests must not weaken, skip or delete accepted expectations merely to pass.

GitHub runs [Verify UniArena](../.github/workflows/verify.yml) on pull requests to `main` and on each push to `main`, including merges. The pull request's Checks tab and the repository's Actions tab report Python, isolated database, university search and offline AI results independently.

The database job discovers all `tests/*_database.mjs` files. To run it locally, point `PGLITE_MODULE` at the installed PGlite 0.5.16 module and run `node --test --test-concurrency=2 tests/*_database.mjs`. Run the browser search check with `node --test tests/university_picker.mjs` and the AI checks with `deno test --deny-net supabase/functions`. The suites use fictional records and simulated external services. Production credentials are unnecessary.

Manually verify the accepted action, rejection without saved-data changes, navigation/resume, and a full stop/start when persistence changes. Check theme/layout changes visually in light and dark mode. Account owners verify real email confirmation/recovery; automated tests must not send real messages.

Record the command, actual result, changed files and any remaining manual limitations in the task/PR. See [Study verification](study-mode-verification.md), [profile scenarios](profile-requirements.md), [restoration checks](launch-and-resume.md), and [current status](implementation-status.md). Older unimplemented test proposals are archived, not current test results.

## Examples for the repository walkthrough

| Workflow | Accepted action | Rejected action | Edge case |
| --- | --- | --- | --- |
| [Battle](../tests/battle_database.mjs) | Two compatible players match and receive a result. | A third player cannot read round progress or report a question in that match. | Repeating a confirmed exit settles the loss once. |
| [Study Together](../tests/study_database.mjs) | Compatible players answer both halves of the same question set. | A player cannot join an expired search. | After 48 hours an unmatched session expires and the player's practice is retained. |
| [Private chat](../tests/chat_database.mjs) | A participant sends a message to a session partner. | An invalid message leaves stored history unchanged. | Retrying the same send creates one message, which survives a process restart. |
| [Deck publication](../tests/decks_database.mjs) | Publish a reviewed deck. | Changed content cannot reuse an earlier review. | Repeating publication returns the existing deck. |
| [Study Plan](../tests/study_plan_database.mjs) | The owner saves and updates a plan. | A different student cannot edit it. | Rejected writes preserve the stored plan. |

### Demonstrate Study Plan ownership

From the repository root, with PGlite 0.5.16 installed as described above, run:

```sh
node --test tests/study_plan_database.mjs
```

The test creates two fictional students in a temporary database. Alice saves and edits a plan. Bob signs in and lists his plans. Alice’s plan is absent. Even when Bob supplies its exact ID, the database rejects his attempts to rename it, replace its calendar entries or delete it. When Alice lists her plans again, hers still has the name she saved.

Show the output line `PASS another student cannot read, change or delete the plan or its calendar entries`. Then open [the SQL function](../supabase/study-plan-schema.sql) and point to `auth.uid()` and `owner_id=me`. The database obtains the student’s identity from the signed-in session and checks ownership on each operation. The [same test](../tests/study_plan_database.mjs) checks that signed-in users cannot read the underlying table directly and that anonymous users cannot call the function.

### Check dependencies before presenting

The [dependency audit](../.github/workflows/dependency-audit.yml) runs on pull requests to `main` and every Monday at 07:17 UTC. It checks the direct and indirect Python packages in the production lock for known vulnerabilities on Linux with Python 3.13. It also checks each deployed AI function against its own Deno lockfile and audits the resolved npm packages, including the Supabase authentication client. To reproduce an Edge Function check, run `deno check --frozen index.ts` followed by `deno audit --frozen --level=low` in its function directory. Development tools are excluded. If a package is flagged, review the advisory, update the affected pin and lockfile, and rerun the audit and the affected workflows.

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

### Matchmaking after switching universities

On 21 November 2026, a demo player switched from NOVA School of Business and Economics — Portugal to UniArena Demo University and saved the profile with no courses selected at the new university. Corporate Finance and Data Visualisation remained listed under NOVA on the profile. Both checks passed on the [public UniArena app](https://uniarena.streamlit.app/).

- **Play → Battle Mode → New Battle.** Neither NOVA course was available to select. The screen stopped before opponent search and showed “Add a course at your current university in Profile to find a Battle opponent.”
- **Play → Study Mode → Study together.** Neither NOVA course was available for a partner session. The screen stopped before partner selection and showed “To find a study partner, choose a course at your current university in Profile and create a deck for it.”

The check ended before any search or invitation was sent. Switching back to NOVA automatically selected both original courses again. After saving, the profile showed both courses with NOVA in parentheses. [University and course changes (PR #115)](https://github.com/maltestodiek/Introduction-to-Programming/pull/115)


## Public workflow rehearsal on 22 November 2026

Two signed-in demo students used Chrome and the Codex browser on the [public UniArena app](https://uniarena.streamlit.app/). The repository baseline was [bec5bb1](https://github.com/maltestodiek/Introduction-to-Programming/commit/bec5bb173b8a210eea8044e2824508a85bbd27cf). For the multiplayer checks, both profiles had Corporate Finance at NOVA and spoke English. Afterward the temporarily switched profile was restored to Bocconi, with Empirical Finance and Risk Management selected again.

- **Friends and chat.** A friend request sent by individual code appeared as outgoing for the sender and pending for the recipient. The recipient's friend count increased from two to three after accepting. The recipient saw an unread message and replied. The reply appeared in the sender's open chat without a manual refresh.
- **Battle score and XP.** Both students finished the same 15-question friend Battle. After rating the deck, one saw a 7–2 win and +40 XP, the other a 2–7 loss and +0 XP. Both views kept their results after a browser reload. The profiles showed 40 and 0 lifetime Battle XP, and the global leaderboard showed the winner on 40 XP.
- **Leaving a Battle.** In a separate accepted friend Battle, **Keep fighting** returned the player to question one. **Leave and lose** then put a 0–0 loss in that player's Recent results with +0 XP.
- **Manual deck and Study Alone.** Reviewing a question with its fourth answer empty showed “Enter Answer 4.” The entered fields remained available for correction. The student supplied the answer, finished a ten-question deck, reviewed and saved it, and completed all ten questions correctly in Study Alone. After reloading, the selected deck showed 33% learning progress, consistent with one correct answer toward the three-correct mastery threshold.
- **Study Plan and calendar export.** The student saved a new Corporate Finance plan using that deck. **Calendar file** downloaded an iCalendar file. Its event contained the saved plan name, ten questions and a 09:00–09:15 session on 22 November. This check covered the download fallback. Direct Google Calendar sync was outside this run.
- **Study Together.** The inviter answered their own ten questions and waited. The friend chose the newly created deck, agreed to share its snapshot and joined. The inviter used **Check for a study partner** to continue. Both answered 20 questions. The first finisher initially saw a waiting result. After the other finished, **Refresh session result** showed a 6/20 win against 2/20, matching the 2/20 loss against 6/20 in the second browser. Both views explained the Study XP rule and availability of the partner deck.

### Battle rating defect found during the rehearsal

On both browsers, closing **Rate this Battle Deck** with its X after the final question left only the navigation visible. Returning to Play → Battle reopened the rating and allowed both students to finish. The local fix keeps the required rating visible and provides a retry if loading the round or saving the rating fails. A Streamlit UI regression test uses simulated read and write failures, retries the same rating and confirms the player returns to Battle. This fix still needs a repeat check after deployment. The rehearsal used two demo accounts and did not measure class-sized load or wait for a 48-hour expiry.
