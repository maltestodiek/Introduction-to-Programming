# Battle round layout

Parent topics: [Battle Mode](../battle-mode.md) and [Appearance and navigation](../appearance-and-navigation.md).

## Why

Players need to see their position, answer outcomes and the remaining server-owned question time without leaving a Battle.

## What

The active Battle round places the question and four answers in a two-column answer layout on the left. A right-side overview shows all 15 question states: correct, incorrect or timed out, the current question, and unopened questions. Above that overview, a **Leave** control requires confirmation that abandoning counts as a loss; confirmation uses the existing server-authoritative abandonment action and returns to the Battle Mode overview. The active Battle dialog cannot be dismissed with its window close control or Escape, so a player cannot leave the UI and later resume without recording a loss. A visible 30-second countdown bar sits beneath the answers, shows only the remaining seconds, and updates locally between server reads so the question and answer controls do not remount each second. At expiry, the server records the timeout and the player receives a **Time has passed** toast. Finishing a player's 15th answer opens a rating popup with Good, Neutral and Bad. Selecting one saves that rating and returns directly to the Battle Mode overview, where the session is Pending until the opponent finishes. The overview reads the current user's persisted answer states, so it remains correct after reopening a Battle.

## Out of scope

Changing Battle scoring, server timing, matching, ratings, Study progress, or any other participant's private answer data.

## Done when

1. An active question shows a shrinking time bar derived from the server's remaining seconds without remounting the question each second; expiry records the server timeout and shows **Time has passed**.
2. The overview shows 15 positions, with correct answers distinct from wrong or timed-out answers.
3. A reopening player sees their saved answer states in the overview.
4. A non-participant cannot read the round overview data.
5. The active Battle dialog cannot be dismissed outside its Leave confirmation. Leaving requires explicit confirmation, records a loss through the existing abandonment rule, prevents any later resume, and returns to the Battle Mode overview. Completing the 15th answer opens the rating popup; selecting a rating returns to the overview without an extra Finish-Battle screen.
