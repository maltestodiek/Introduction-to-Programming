# Friends header button

Parent topics: [Appearance and navigation](../appearance-and-navigation.md) and [Social connections](../social-connections.md).

## Why

Friends is an account-level destination like Profile and Chats, not a study activity. Keeping it among the large activity tabs crowded the main navigation.

## What

Navigation is a fixed left sidebar on desktop. The logo appears at the top, followed by Decks, Play, Leaderboard and Study Plan. A divider separates these activity destinations from Friends, Chats and Profile. The Friends icon opens the unchanged Friends page; the Profile avatar remains the final item in the account/social group. Like Chats, Friends is shown once the user has a profile. On narrow screens the sidebar returns to normal document flow so it does not cover page content.

## Out of scope

Changing the Friends page itself, friend codes, invitations, requests, chat, the Leaderboard's Friends ranking, or any database rule.

## Done when

1. The large tabs are exactly Decks, Play, Leaderboard and Study Plan.
2. On desktop, the sidebar shows the logo above four activity destinations, then Friends, Chats and Profile as a separate account/social group below a divider.
3. Clicking the header Friends button opens the Friends page.
4. The account/social group remains visually separate from the four activity destinations.
5. A pending invitation can still be accepted from the Friends page.

Checks: `tests/test_friends_header.py`, `tests/test_friends.py`, plus a manual look in the running app.
