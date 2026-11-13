# Battle Mode — planned competitive experience

## Why
Offer competitive course quizzes separately from non-rewarded Study sessions.

## What
The redesigned Battle Mode entry currently shows Coming soon. Its proposed Battle Pool, 15-question sampling and creator rewards are not implemented or approved as the next task. Preserve the [team proposal](../docs/archive/specifications/battle-pool-and-study-proposal.md) for review; its old fixed-20-question Study proposal is superseded by [Study Mode](study-mode.md).

An earlier classic duel engine already exists: friend invitations, mutual one-hour random searches, 30 shared questions (15 from each deck), compatible course/language, server-owned timers, a 24-hour deadline, ratings, and once-only XP/streak settlement. It supports saved round resumption and review, while its old create-session lobby is no longer shown on Play. See [classic duel rules](../docs/archive/specifications/classic-duels.md). Do not silently replace historical snapshots, results or scores.

## Out of scope
Implementing new Battle Pool logic or new rewards as part of documentation cleanup; changing the existing Study rules or real saved matches.

## Done when
Before implementing the new mode, the group reviews a concrete task with allowed/rejected/restart scenarios and explicit differences from classic duels. Preserve existing regression coverage (`tests/test_play.py`, `tests/test_play_ui.py`, `tests/play_database.mjs`). Claim the redesigned Battle Mode is complete only after its own reviewed checks and manual workflow pass.
