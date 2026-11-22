# Appearance and navigation

## Why
Keep UniArena readable, recognizable and consistent across screens, themes and devices.

## What
Group branding, light/dark/system themes, backgrounds, icon design, hover animations, layout and navigation in this feature. Use the facing-flashcards logo, indigo primary actions and mint highlights; mint surfaces use dark text. See [brand assets](../docs/branding.md).

Native Streamlit appearance settings control the browser's theme preference. Custom cards, avatar backgrounds, university search, dialogs and controls must adapt. Uploaded photos are not recoloured. Maintain readable text, labels and focus indicators in both themes. Battle setup, session cards and answer feedback follow the current theme, as do Friends requests, friend codes and invitation sharing controls.

Use consistent vector/Material icons instead of emoji. Book and crossed-swords mode cards and navigation use hover/focus effects, disabled for reduced-motion preferences. The welcome screen shows the animated logo and Start; authentication/session restoration is owned by [Authentication and Profiles](authentication-and-profiles.md).

Top navigation: Decks, Play, Leaderboard and Study Plan; Profile, Friends and Chats appear in the header (see [Friends header button](tasks/friends-header-button.md)), and the Profile button carries the user's picture (see [Profile button avatar](tasks/profile-button-avatar.md)). Leaderboard and Study Plan remain placeholders. Below the divider, Friends, Chats and Profile use the same icon and label columns as Decks, Play, Leaderboard and Study Plan. Icons share a left-hand column, and labels are centered in the remaining space. Both are vertically centered, including when Chats shows an unread count. Clicking Study Mode reveals Study alone and Study together within the mode card before settings open.

Play initially displays only separate Battle and Study cards; the selected mode contains its own session controls. Solo cards have no partner actions. Partner menus link to Social Connections.

Learning-level selections use real colour swatches and readable names, with an info-only legend control. Show question preferences below What do you want to focus on? Keep the calculator beside the quiz on desktop. On wide, tall windows keep the chat composer visible while messages scroll. On narrower or shorter windows allow the whole page to scroll so the conversation and composer remain reachable. Use a narrower labeled sidebar at tablet widths and compact navigation above the page on phones.

## Out of scope
Changing study scoring, stored avatar character design, authentication, matching, message permissions or database rules while making visual changes.

## Done when
Light and dark surfaces remain readable, including popovers and university search. Keyboard navigation and reduced-motion support work. The Play landing page keeps its two mode cards clear of dashboard content. Chat and calculator do not obscure required controls at supported viewport sizes. Verify visually in the running app; theme preferences survive browser reloads independently of account data.

Checks: `tests/test_appearance.py`, `tests/test_navigation.py`, `tests/test_launch.py`, `tests/test_study_ui.py`, `tests/test_chat.py`, plus manual layout checks.
