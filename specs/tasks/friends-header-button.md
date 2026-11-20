# Friends header button

Parent topics: [Appearance and navigation](../appearance-and-navigation.md) and [Social connections](../social-connections.md).

## Why

Friends is an account-level destination like Profile and Chats, not a study activity. Keeping it among the large activity tabs crowded the main navigation.

## What

Friends is removed from the row of large navigation tabs. The logo sits above a wide navigation band holding Decks, Play, Leaderboard and Study Plan. Friends, Chats and Profile form a distinct icon-only account/social group to the right of that band. The Friends icon opens the unchanged Friends page; the Profile avatar remains the final item in the group. Like Chats, Friends is shown once the user has a profile.

## Out of scope

Changing the Friends page itself, friend codes, invitations, requests, chat, the Leaderboard's Friends ranking, or any database rule.

## Done when

1. The large tabs are exactly Decks, Play, Leaderboard and Study Plan.
2. The header shows the logo above four wide activity tabs, then Friends, Chats and Profile as a separate icon-only group to their right.
3. Clicking the header Friends button opens the Friends page.
4. The account/social icon group remains visually separate from the four activity tabs.
5. A pending invitation can still be accepted from the Friends page.

Checks: `tests/test_friends_header.py`, `tests/test_friends.py`, plus a manual look in the running app.
