# Full-height sidebar

Parent topic: [Appearance and navigation](../appearance-and-navigation.md). Builds on [Friends header button](friends-header-button.md).

## Why

The desktop navigation looked like a floating card beside the page. A continuous bar along the left edge reads as the app's frame, separates navigation from content more clearly and leaves the content area uncluttered.

## What

On desktop the sidebar runs the full height of the window, flush with the left edge, with a thin divider line on its right instead of a rounded, outlined card. The logo sits at the top, followed by Decks, Play, Leaderboard and Study Plan, a divider, then Friends, Chats and Profile, unchanged in order and behaviour. The page content starts to the right of the bar and is never covered by it. On narrow screens the sidebar keeps returning to normal document flow.

The change is visual only and adds no state or persistence.

## Out of scope

Changing navigation destinations, their order or labels, the active-item highlight, the Chats dropdown, the Profile avatar, page content or any database rule.

## Done when

1. Allowed: every sidebar button still opens the same page as before.
2. Rejected: on narrow screens the sidebar does not cover page content.
3. Restart: after a new sign-in the sidebar appears the same way, with Play highlighted.
4. On desktop the sidebar reaches from the top to the bottom of the window along the left edge, without rounded corners or a card outline, and the main content is laid out beside it.

Checks: `tests/test_friends_header.py`, plus a manual look in the running app in light and dark theme.
