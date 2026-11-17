# Friends header button

Parent topics: [Appearance and navigation](../appearance-and-navigation.md) and [Social connections](../social-connections.md).

## Why

Friends is an account-level destination like Profile and Chats, not a study activity. Keeping it among the large activity tabs crowded the main navigation.

## What

Friends is removed from the row of large navigation tabs, which now holds Decks, Play, Leaderboard and Study Plan. A Friends button appears in the header between Profile and Chats, the same size as the Profile button, with the existing Friends icon and the same hover, focus and reduced-motion behaviour. It opens the unchanged Friends page. Like Chats, it is shown once the user has a profile.

## Out of scope

Changing the Friends page itself, friend codes, invitations, requests, chat, the Leaderboard's Friends ranking, or any database rule.

## Done when

1. The large tabs are exactly Decks, Play, Leaderboard and Study Plan.
2. The header shows Profile, then Friends, then Chats.
3. Clicking the header Friends button opens the Friends page.
4. A pending invitation can still be accepted from the Friends page.

Checks: `tests/test_friends_header.py`, `tests/test_friends.py`, plus a manual look in the running app.
