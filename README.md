# StudyDuel

StudyDuel uses Python and Streamlit for its interface and Supabase for authentication, shared data and profile images. Features: student profiles, friends and manual quiz-deck creation.

## Run locally

Install uv, then from this folder:
- uv sync
- uv run pytest -q
- uv run streamlit run app.py

Open http://localhost:8501. The local secrets file is configured on this computer and ignored by Git. Teammates should copy .streamlit/secrets.toml.example to .streamlit/secrets.toml and supply the project URL and publishable key.

## Available now

Sign up, confirm email, sign in and sign out. Choose a username, university, courses and languages. Customize an avatar or upload and crop a photo. Save and edit the profile. XP and streak begin at zero. Add friends using codes and invitation links.

Universities can be searched live through the ROR API, with country labels and manual entry for missing institutions. University selection opens a dropdown with search at the top and a manual-entry fallback. No prototype institution is offered. Courses can be typed in. Degree level and field of study are optional and private. Shared course discovery is future work. The avatar editor supports sideways swipes, arrows, keyboard navigation, and category tabs with immediate character previews. Decks, games and earned XP are not yet implemented. The app is hosted at https://studyduel-nova.streamlit.app.

## Data and privacy

Supabase Auth owns account credentials. profiles contains fields visible to signed-in students. profile_private contains owner-only courses and avatar settings. profile-images is a private Storage bucket: other signed-in users can read only an image referenced by an active profile. XP and streak fields are not client-editable. SQL setup is recorded in supabase/profile-schema.sql; it and supabase/profile-options-update.sql are already applied to the StudyDuel project and should not be rerun there.

Returning browsers can restore a Supabase-verified session and the last saved screen. Passwords are never saved; sign out on shared devices. Invalid sessions return to sign-in. See docs/launch-and-resume.md.

## Verify

Run the automated tests, then create an account with your own email, confirm it, sign in, save a profile, sign out and sign in again. Stop Streamlit and restart it, then verify the saved profile remains after signing in. Check photo/avatar switching and invalid inputs.

Live email delivery depends on the project's email configuration. Default Supabase email service may restrict recipients; wider testing may require SMTP configuration.

## Structure

app.py: screens; auth.py: authentication; logic.py: validation and images; db.py: profile persistence; tests/: automated checks; docs/: product and verification; specs/: feature plans; supabase/: database setup.

Password recovery uses Supabase email links and a new-password form. The local app must be running when the link opens. Live email delivery still needs a user-run check.

## Reliable local launch on this Mac
Run `sh run-app.sh` to start StudyDuel and `sh run-tests.sh` for verification. These use uv and the locked dependencies, with the environment and compiled cache under `~/Library/Caches/StudyDuel` to avoid the stalled Desktop environment/cache. The original `.venv` remains untouched. No Supabase data or credentials were moved.

## Friends
Each completed profile receives a stable eight-character friend code. Find a friend by code and send a request; only the recipient can accept or decline it. The sender can cancel it. Accepted friendships appear in both accounts and either participant can remove them.

Invitation links require explicit acceptance after sign-in and profile completion. They expire after seven days; creating a new one replaces the old one. Copy link, WhatsApp, email and native sharing leave sending under the user's control. The link token is shown only in the creating session and stored as a digest in Supabase.

`supabase/friends-schema.sql` was applied on 11 November 2026; do not rerun it on this project. `tests/sql/friends_acceptance.sql` exercises synthetic identities with rollback; it must never be changed to operate on actual student records. The only wildcard authentication redirect is the app's own `/?invite=*` route. No gameplay or messaging APIs are included.

## Manual decks
Open Decks after completing your profile. Choose Create New Deck, use one of your selected courses, and enter exactly 15 questions with four answers and one correct answer each. Any draft card can be edited or deleted. Save Deck opens the mandatory review; Create Deck publishes the reviewed version. Published decks and solutions are read-only and shared with signed-in students at your university. Anki and AI creation are disabled Coming soon options.

Decks live in Supabase, not browser storage or local SQLite. Unpublished drafts live in the current session and are lost after a full reload. The private review snapshot enforces exact-content confirmation; publication is atomic and retry-safe. `supabase/decks-schema.sql` is already applied to the current project; do not rerun it there.

The English concept is available in `docs/overall-concept-en.md` and `docs/StudyDuel Overall Concept v2 English.docx`. The original German document remains under docs/source. Historical technology proposals in the translation are not implementation instructions. `specs/third-feature.md` governs the active deck workflow.

## Isolated database checks
Python tests use mocks. For actual SQL and RLS checks, install `@electric-sql/pglite@0.5.16` in a temporary tooling folder and run `tests/decks_database.mjs` with Node, setting `PGLITE_MODULE` to its module path if it is not resolvable normally. This starts a temporary PostgreSQL-compatible database, applies the real deck migration with minimal auth/profile fixtures, checks authorization and atomicity, and reopens the database from a fresh process. It never contacts Supabase and removes its temporary data afterward. Node is a test tool only; the application remains Python/Streamlit.

### Play
The Play tab supports accepted friend challenges and mutual random matching. Choose a course and a published deck in one of your profile languages. Random searches last one hour and can be cancelled; refreshing does not renew them. A friend without the course requires an explicit warning confirmation. Both profiles and both decks must support the same language. Creators can set a missing language on older decks once, from the deck view.

Apply `supabase/play-schema.sql` once after the deck migration before deploying this version. It adds private queues, invitations, presence, duels and round progress; only authenticated participant-checked RPCs can access them. Existing deck content is retained. No new secrets or API services are needed. Multiplayer data lives in Supabase, not on Streamlit's temporary disk.

Each player answers 30 questions with a server-owned 30-second timer per question, then rates both distinct decks. Both players have 24 hours from matching/acceptance. Answers and XP settlement are transactional and retry-safe. Expired duels are settled on the next participant request; there is no background scheduler. Play refreshes its lobby every ten seconds. A single database advisory lock serializes short Play transactions for this class release; a larger deployment should move to narrower locks and paginated history. Browser closure retains progress and timers; reopen Play and choose Resume round.

Verification: `sh run-tests.sh` includes Play UI and repository checks. `tests/play_database.mjs` runs the actual migration/RPCs in an isolated PGlite PostgreSQL instance, with a separate-process persistence check. Set `PGLITE_MODULE` to the installed `@electric-sql/pglite` module and run the file with Node. Node is test tooling only; the app remains Streamlit/Python.

Manual walkthrough with two group accounts:
1. Both select the same university, course and compatible profile/deck language. Open Play, choose a deck, and click Find random player on both accounts. With only one opt-in, no match should be created. Cancel a search to remove eligibility.
2. Alternatively, invite an accepted friend. Verify the missing-course warning and explicit override, then select a deck and Accept invitation on the recipient's account. Decline/cancel must not award XP.
3. Start a round, answer a question and reload. Resume must retain progress. Let a question expire; it scores zero. Try leaving through Profile and cancel the abandonment prompt.
4. Finish all 30 questions and rate the decks on both accounts. Check score comparison and XP, then reload to confirm XP is not awarded twice.
5. Stop and restart the app process. Sign in again if necessary, open Play, and verify the same saved match/progress/results. Refresh alone is not a process restart.
