# StudyDuel

First working feature: Supabase email/password authentication and editable student profiles.

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

Login sessions are per browser connection and are not saved to disk. Restarting or reloading may require sign-in again. Profile data remains in Supabase.

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
