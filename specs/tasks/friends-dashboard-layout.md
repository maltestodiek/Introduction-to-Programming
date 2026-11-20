# Friends dashboard layout

Parent topics: [Social connections](../social-connections.md) and [Appearance and navigation](../appearance-and-navigation.md).

## Why

The Friends screen contains several related actions, but its vertical form flow makes relationships, invitations and study actions difficult to scan.

## What

Arrange Friends as a desktop-friendly social dashboard. The main column shows incoming requests, accepted friends and university suggestions. A companion Invite friends card holds the current user's stable friend code, exact-code lookup and invitation-link controls. After a successful lookup, show the public profile preview with View profile and Add actions in that card. Put a local search field beside the accepted-friends heading; it filters accepted friends only and does not search profiles or expose friend codes. Accepted-friend rows retain Chat, Battle challenge, Study together and removal actions.

Use only persisted relationship, invitation and profile data. Do not display invented online status, mutual-deck counts, Battle records or notifications.

## Out of scope

Changing friend authorization, invitation expiry, directory privacy, chat rules, Battle matching, Study matching or the database schema.

## Done when

1. The Friends screen has clearly separated Friends and Invite friends areas on desktop.
2. Incoming requests retain Accept and Decline, and sent requests retain Cancel.
3. An accepted friend still opens Chat, Battle setup and Study Together setup; removal remains confirmed.
4. The local search filters visible people only and cannot enumerate profiles or friend codes.
5. Friend code, invitation creation/revocation and exact-code requests work after a process restart.

Checks: `tests/test_friend_list_chat.py`, `tests/test_friends.py`, `tests/test_friends_header.py`, plus a manual desktop and narrow-screen check.
