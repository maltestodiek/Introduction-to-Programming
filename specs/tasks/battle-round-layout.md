# Battle round layout

Parent topics: [Battle Mode](../battle-mode.md) and [Appearance and navigation](../appearance-and-navigation.md).

## Why

Players need to see their position, answer outcomes and the remaining server-owned question time without leaving a Battle.

## What

The active Battle round places the question and four answers in a two-column answer layout on the left. A right-side overview shows all 15 question states: correct, incorrect or timed out, the current question, and unopened questions. **Save and exit** shows the finish deadline and returns to Active battles with progress saved. A visible 30-second countdown bar sits beneath the answers, shows only the remaining seconds, and updates locally between server reads so the question and answer controls do not remount each second. At expiry, the server records the timeout and the player receives a **Time has passed** toast. Finishing a player's 15th answer opens a rating popup with Good, Neutral and Bad. Selecting one saves that rating and returns directly to the Battle Mode overview, where the session stays in Active battles until the outcome is known. The overview reads the current user's persisted answer states, so it remains correct after reopening a Battle.

## Out of scope

Changing Battle scoring, server timing, matching, ratings, Study progress, or any other participant's private answer data.

## Done when

1. An active question shows a shrinking time bar derived from the server's remaining seconds without remounting the question each second; expiry records the server timeout and shows **Time has passed**.
2. The overview shows 15 positions, with correct answers distinct from wrong or timed-out answers.
3. A reopening player sees their saved answer states in the overview.
4. A non-participant cannot read the round overview data.
5. Save and exit shows the deadline before returning to the overview. Resume opens the saved round without resetting either timer. Completing the final question makes the rating available.
