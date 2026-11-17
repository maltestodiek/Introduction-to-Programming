# Play as the landing page, and the logo as a way back

Parent topic: [Appearance and navigation](../appearance-and-navigation.md).

## Why

Students come to StudyDuel to play and study. After signing in they landed on their Profile and had to click once more to start; there was also no single "home" control.

## What

After signing in, a user with a profile lands on Play instead of Profile. The StudyDuel logo and wordmark in the header are one button that opens Play from any page, keeping the logo artwork, the two-colour wordmark, a visible keyboard focus indicator and the usual confirmation when leaving an active round.

A browser that restores a remembered session still resumes the page it was last on, as described in [Welcome and returning users](../../docs/launch-and-resume.md). A new user without a profile still completes profile setup first.

## Out of scope

Changing Play itself, the Profile page, sign-in, session restoration rules, or what is stored in the browser beyond the default page name.

## Done when

1. A signed-in user with a profile and no remembered page sees Play first.
2. Clicking the header logo from another page opens Play.
3. A remembered page is still restored for a returning browser.
4. A user without a profile still sees profile setup.

Checks: `tests/test_play_landing.py`, `tests/test_launch.py`, plus a manual look in the running app.
