# Authentication and student profiles

## Why
Give each student a verified identity and a reusable, privacy-controlled study profile.

## What
Use Python, Streamlit and Supabase Auth, Database and Storage. Support email/password signup with email confirmation, sign-in, sign-out and Supabase password recovery. Verify identity remotely; never authenticate from browser-supplied user IDs. Preserve entered values after validation failures and show username guidance below its field. Clear passwords after successful authentication.

Require a unique username, university, courses and languages. Offer ROR university search with a manual-entry fallback, manual course entry, optional degree level and field of study, and optional expected graduation year (2000–2100). Show the degree below university and graduation year when supplied. Private fields stay private; see [profile requirements](../docs/profile-requirements.md) for exact visibility and image validation rules.

Allow a cropped photo or a customizable avatar with skin colours, ten hairstyles and ten accessories plus None. Keep swipe/arrow/keyboard navigation and consistent high-resolution images in summaries, participant menus and chats. Profile edits cannot alter XP, streaks or friendship records.

Returning browsers restore only a Supabase-verified session and minimal navigation state. Sign-out clears saved session information. A full process restart preserves database records; expired/revoked sessions return to sign-in. See [session restoration](../docs/launch-and-resume.md). This supersedes the original no-session-restoration proposal.

## Out of scope
Social login, shared university course discovery, new matching rules, and earning XP through profile edits. Friendship and messages are covered by Social Connections.

## Done when
Valid signup requires confirmation; invalid credentials never authenticate. Required profile fields and images are validated without losing valid input. A second user cannot read private fields or edit the first user's profile. Avatar/photo switching and graduation year persist across a process restart. Recovery, logout, invalid tokens, disabled browser storage and separate-user sessions are tested. Live email delivery must be verified separately by the account owner.

Checks: `tests/test_auth_acceptance.py`, `tests/test_profiles.py`, `tests/test_profile_changes.py`, `tests/test_recovery.py`, `tests/test_launch.py`, `tests/test_graduation.py`, `tests/test_universities.py`, `tests/test_storage.py`, `tests/test_ui.py`.
