# First feature Supabase authentication and profile setup

## Why
StudyDuel needs a real identity for each student before building user-owned decks and duels. The user selected Supabase and email/password on 11 November 2026, superseding the demo-user-only scope.

## What
Keep Python, Streamlit, uv, and pytest. Use Supabase Auth for signup, confirmation, sign-in, identity verification, and sign-out. Keep SQLite reserved for future class application data; never store passwords or authentication tokens in it.

Show Sign in and Create account forms in English. Signup requires email, password, matching password confirmation, and a unique username. Use the project's configured password policy; proposed minimum is eight characters. Do not trim or silently alter passwords. Trim outer whitespace on email. Incomplete/invalid input never contacts Supabase.

Keep email confirmation enabled. Signup without a session displays a generic instruction to check email and never opens the signed-in screen. Only a Supabase-verified user associated with a valid session can see the signed-in welcome screen. Wrong credentials, expired/invalid sessions, and network errors fail closed without displaying raw provider errors or tokens.

Create an auth client per Streamlit session, never in a global cache. Verify identity with get_user rather than trusting a UI flag or only reading a cached session. Preserve all form fields after invalid submission so the user can correct them; clear password fields after successful signup or login. Sign out clears local auth and user-specific state even if the remote request fails; explain that remote sign-out could not be confirmed. Tokens stay only in server session memory. A new browser session or full process restart requires login again; the Supabase account persists.

Use project URL and publishable key from ignored environment/Streamlit configuration. Never use service-role/admin credentials. A missing configuration shows setup guidance and leaves the app locked. No external signup emails are sent by automated tests.

## Profile setup
After confirmed login, complete the required university, courses, and languages. Offer a cropped photo upload or customizable avatar, with a default avatar when skipped. Implement the visibility, persistence, editing, and ownership rules in docs/profile-requirements.md. Include a profile screen showing XP and win streak initialized to zero and an empty friends list; earning XP and managing friendships come later.

## Out of scope
Deck creation, duels, friend search, social login, persistent login cookies, public deployment, and automatic publishing to GitHub. Password reset is a follow-up before a public launch.

## Done when
1. Valid signup with confirmation enabled asks the student to check email and does not authenticate them.
2. After confirmation, valid credentials produce a verified welcome screen. Wrong credentials or unconfirmed email leave the app signed out.
3. Sign out removes access; provider failure still clears local access.
4. A fresh session cannot inherit another user's identity. Restarting the app returns to login, and the same confirmed account can sign in again.
5. Missing config, invalid input, expired session, and a provider outage display safe messages and never unlock the app.
6. Tests use a fake provider. A separate live walkthrough verifies signup email delivery, confirmation, login, logout, and restart against the new Supabase project.

7. All six profile acceptance scenarios in docs/profile-requirements.md pass, including restart persistence, image switching, and cross-user access checks.


User extension: Supabase password recovery is now in scope. Send a reset email, consume and verify the recovery session, validate the new password and confirmation, update through Supabase, and return to sign-in. Never log recovery tokens. Email delivery and the real recovery link require a user-run walkthrough.
