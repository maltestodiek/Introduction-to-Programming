# Arena logo

Parent topic: [Appearance and navigation](../appearance-and-navigation.md). Brand notes: [branding](../../docs/branding.md).

## Why

The app is called UniArena, and its logo should show an arena while staying recognisable as the same product.

## What

The logo keeps the two facing flashcards with the lightning-bolt gap and places them in an oval arena: an outer wall and a pitch edge with shaded seating between them, indigo on the left and mint on the right. The small spark lines are gone.

The logo has a transparent background and is shown directly on the page, with no box or badge around it, in the header button, on the sign-in screen and on the welcome screen. It is displayed whole, not cropped. The browser-tab icon uses the same image.

## Out of scope

Changing the colour palette, the wordmark, the navigation icons, avatars, or the hosted address.

## Done when

1. The header, sign-in and welcome screens show the arena logo, whole and without a box around it.
2. The logo is readable on the light and the dark theme backgrounds.
3. The logo file has a transparent background and contains both brand colours.
4. The header logo still opens Play and keeps its focus indicator.

Checks: `tests/test_branding.py`, `tests/test_play_landing.py`, `tests/test_launch.py`, plus a manual look in both themes.
