# Battle question reports

Parent topics: [Battle Mode](../battle-mode.md) owns the completed Battle and authorization; [Appearance and navigation](../appearance-and-navigation.md) owns the review control.

## Why

Players need a direct way to flag a flawed Battle Deck question while reviewing a completed Battle, without changing the immutable snapshot or exposing another player's answers.

## What

Each expanded question in a completed Battle review offers **Report this question**. The reporting participant chooses one of **Incorrect answer**, **Question is unclear**, or **Other**, and may add an optional comment of up to 500 characters. A report is durable and is limited to one report per participant, Battle session, and question. Reopening the review after a restart preserves that limit.

Only a participant in a settled Battle may report one of its fifteen snapshot questions. Reporting never edits the Battle Deck, changes scores, ratings, Battle XP, Study progress, or exposes reports to other players. The current UI confirms a saved report; reviewing reports and moderation are not part of this task.

## Out of scope

Deck removal, moderation queues, creator notifications, reports during an unfinished Battle, rating changes, and reports for Study questions.

## Done when

- A completed Battle participant can submit one valid report for an individual review question.
- A second attempt for the same session/question by the same participant does not create another record.
- A non-participant, an active Battle, an invalid question number, invalid reason, or a comment over 500 characters is rejected without a saved record.
- The report remains saved after a process restart and does not alter Battle or Study state.
