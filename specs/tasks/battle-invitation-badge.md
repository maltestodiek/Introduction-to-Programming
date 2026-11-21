# Battle invitation badge

Parent topics: [Battle Mode](../battle-mode.md) and [Appearance and navigation](../appearance-and-navigation.md).

## Why

An incoming Battle invitation can otherwise be missed while a student is elsewhere in the app.

## What

When the signed-in student has one or more pending incoming Battle invitations, the Play item in the left navigation shows a compact **1** badge on its right edge, inside the existing Play button. The badge uses the server-authoritative incoming-invitation list and therefore disappears after all invitations are accepted, declined, cancelled or expired.

Random matchmaking has no identified recipient while it searches, so it does not create a navigation badge before a match exists.

## Out of scope

Browser push notifications, persisted read/unread state, changes to Battle matching, and changes to invitation authorization.

## Done when

1. An allowed incoming Battle invitation shows a **1** badge inside Play.
2. A sender's outgoing invitation does not show a badge for that sender.
3. After an invitation is accepted, declined, cancelled or expired, it no longer contributes to the badge, including after a restart.
4. The Play button continues to navigate normally and the badge remains readable on supported desktop and narrow layouts.
