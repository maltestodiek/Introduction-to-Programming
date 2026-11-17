# Appearance and navigation

## Why
Keep StudyDuel readable, recognizable and consistent across screens, themes and devices.

## What
Group branding, light/dark/system themes, backgrounds, icon design, hover animations, layout and navigation in this feature. Use the facing-flashcards logo, indigo primary actions and mint highlights; mint surfaces use dark text. See [brand assets](../docs/branding.md).

Native Streamlit appearance settings control the browser's theme preference. Custom cards, avatar backgrounds, university search, dialogs and controls must adapt. Uploaded photos are not recoloured. Maintain readable text, labels and focus indicators in both themes.

Use consistent vector/Material icons instead of emoji. Book and crossed-swords mode cards and navigation use hover/focus effects, disabled for reduced-motion preferences. The welcome screen shows the animated logo and Start; authentication/session restoration is owned by [Authentication and Profiles](authentication-and-profiles.md).

Top navigation: Decks, Play, Friends, Leaderboard and Study Plan; avatar, Profile and Chats appear in the header. Leaderboard and Study Plan remain placeholders. Clicking Study Mode reveals Study alone and Study together within the mode card before settings open.

Play displays Create new session, Ongoing sessions, then Session history. Separate Battle and Study cards; solo cards have no partner actions. Show completed/expired/cancelled Study history and completed Battle history with actions to reopen/review. Partner menus link to Social Connections.

Learning-level selections use real colour swatches and readable names, with an info-only legend control. Show question preferences below What do you want to focus on? Keep the calculator beside the quiz on desktop. Keep the chat composer visible and only its message area scrollable.

## Out of scope
Changing study scoring, stored avatar character design, authentication, matching, message permissions or database rules while making visual changes.

## Done when
Light and dark surfaces remain readable, including popovers and university search. Keyboard navigation and reduced-motion support work. Creation appears above ongoing sessions and history. Chat and calculator do not obscure required controls at supported viewport sizes. Verify visually in the running app; theme preferences survive browser reloads independently of account data.

Checks: `tests/test_appearance.py`, `tests/test_navigation.py`, `tests/test_launch.py`, `tests/test_study_ui.py`, `tests/test_chat.py`, plus manual layout checks.
