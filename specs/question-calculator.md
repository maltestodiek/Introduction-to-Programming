# Per-question calculator

## Why
Authors need to permit basic arithmetic for selected quiz questions.

## What
Both deck editors offer an unchecked Allow calculator for this question setting. It is a strict boolean saved with question content and shown during review. Old questions default to disabled. Active sessions and received deck copies retain the setting from their immutable snapshot. Changing the permission alone does not reset learning progress.

During an enabled question, offer a Calculator popover with digits, decimals, addition, subtraction, multiplication, division, brackets, backspace, clear and equals. Keep the expression visible and display the result separately, right-aligned. Use distinct button colours for numbers and functions. Include square roots and integer powers from −12 to 12. Calculations never submit an answer, change progress, or pause a duel timer. Use bounded arithmetic parsing in Python, never eval or an external API. Each session/question has separate calculator state.

## Out of scope
Trigonometry, logarithms, graphing, external APIs, and preventing use of a physical calculator or another application.

## Done when
Basic arithmetic and precedence work; invalid expressions and division by zero show readable errors. Disabled questions have no calculator. The setting survives validation, review, save and reload. Changes to a source deck do not change existing session permissions. Calculator interaction never sends an answer. Existing Study and Play acceptance checks remain green.
