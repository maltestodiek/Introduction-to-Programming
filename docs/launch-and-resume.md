# Welcome and returning users

First visits show the large animated logo and Start button. Start opens account creation/sign-in. Reduced-motion preferences disable the animation. Returning browsers skip the welcome screen and retain the selected account tab.

This user-requested extension supersedes the original authentication requirement to forget authentication after a process restart. Browser localStorage holds Supabase access/refresh tokens and minimal navigation state. Passwords, profile drafts, uploaded photos and recovery links are never stored there. Always sign out on shared devices. Clearing site data removes remembered sign-in.

On a fresh app session, Supabase set_session refreshes expired access tokens, and get_user verifies identity before profile access. A browser-supplied user ID never grants access. Invalid/revoked sessions return to sign-in. Profile/edit navigation resumes only for the verified matching account; saved profile fields load from Supabase. When a student reopens the app in the same browser after leaving Study alone or Study together setup, the last setup screen and its settings return. These include the course, deck, levels, solo chapters and length, or partner type, eligible friend, total questions and an available invitation or open session. The app checks choices against the current account’s available options. Sharing consent requires a fresh confirmation after reopening. Starting or joining still requires pressing Start studying. Leaving for another main tab replaces the remembered destination. In-progress rounds remain accessible from the ongoing sessions list. Other unsaved form edits are local to the running session.

Token refresh runs on interaction, not in a background timer, so rotated tokens are immediately written back to browser storage. Sign-out clears remembered tokens even when remote sign-out fails. Password recovery takes precedence over restoring a normal session. If browser storage is blocked, the app still works for the current session.

Verification: open a fresh browser, observe welcome, select Start, choose Create account, refresh and confirm the same account tab. With a test account, sign in, refresh/restart the app and confirm the profile reloads; select Edit profile and refresh to restore that screen. Sign out and refresh: no signed-in access should return. Test password recovery and invitation links separately.

References: https://supabase.com/docs/reference/python/auth-setsession and https://supabase.com/docs/reference/python/auth-getsession
