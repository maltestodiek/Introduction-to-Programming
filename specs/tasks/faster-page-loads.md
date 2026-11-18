# Faster page loads

Parent topic: [Appearance and navigation](../appearance-and-navigation.md). Session rules: [Welcome and returning users](../../docs/launch-and-resume.md).

## Why

Every click reran the whole app and repeated the same work: it sent the full-size logo and avatar to the browser again, re-read the profile with two database queries, re-rendered the avatar, re-downloaded a profile photo and asked Supabase to confirm the signed-in user. The database is in Frankfurt and the hosting is in the United States, so each of those round trips is slow.

## What

- **Images:** the header and sign-in screen use a small copy of the logo, and the header Profile button a small copy of the user's picture. The welcome screen uses a medium copy. The files in the repository are unchanged.
- **Avatar and photo:** a rendered avatar is reused until its settings change; a profile photo is downloaded once per session and again only when its path changes.
- **Profile data:** the saved profile is reused for up to 20 seconds while browsing. It is always read fresh on the Profile page, while editing, and after any profile or course save, so XP, streak and edits shown there are current.
- **Sign-in check:** Supabase is asked to confirm the signed-in user at most once a minute instead of on every click. Token refresh still happens on every interaction. A revoked session therefore ends within a minute, not instantly.
- **Chat inbox:** the Chats button checks for new messages every 15 seconds instead of every 5. An open conversation still updates every 3 seconds.

## Out of scope

Hosting, the database region, caching of decks, sessions, friends or leaderboards, and any change to what data is stored or who may read it.

## Done when

1. A normal page sends less than a third of the previous image data to the browser.
2. Browsing between pages within 20 seconds reads the profile once; the Profile page and saves always read it fresh.
3. The signed-in user is confirmed at most once a minute, and a session that fails confirmation still ends.
4. Logo, avatar and photos look the same as before.

Checks: `tests/test_page_speed.py`, `tests/test_launch.py`, `tests/test_auth_acceptance.py`, plus timing a few page changes in the running app before and after.
