# Battle overview layout

Parent topics: [Battle Mode](../battle-mode.md) and [Appearance and navigation](../appearance-and-navigation.md).

## Why

The wide, ungrouped Battle overview made it difficult to scan available actions and compare ongoing, pending and completed Battles.

## What

Battle Mode opens with a compact indigo-to-mint summary hero. It shows durable Battle XP, the win/loss record, and the signed-in player's real global Leaderboard rank, plus **New Battle**. If the read-only Leaderboard is temporarily unavailable, the rank is omitted while Battle remains usable. A single Game Overview card beneath it shows Ongoing and Pending as two lanes side by side, with Recently completed as a full-width lane below whose cards sit three abreast. Every Battle renders as a versus card: the player\u2019s and the opponent\u2019s initial around a VS tag, with the deck name as a subline. Ongoing cards pulse and keep Start/Resume; pending cards show the own result large with a waiting indicator; completed cards show the stored score large with a Win/Loss pill, the Battle-XP delta as a chip and a green or red edge, and keep Review. Searches keep Cancel and their live one-hour countdown. Empty lanes show a friendly empty state. Pending random searches retain their live one-hour countdown.

## Out of scope

Leaderboard ranking, new Battle data, matching rules, scoring, timing and session actions.

## Done when

1. The hero shows the profile's Battle XP, persisted win/loss record and real Leaderboard rank without invented statistics.
2. New Battle, Start/Resume, Cancel search and Review trigger their existing actions.
3. Ongoing, Pending and Completed statuses remain correctly separated in the compact overview.
4. The overview is readable in light and dark themes and collapses cleanly on narrow screens.
