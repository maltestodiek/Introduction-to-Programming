# Calculator result rounding

Parent topic: [Deck authoring](../deck-authoring.md), per-question calculator.

## Why

Results with many decimal places, such as 1 ÷ 3, ran out of the calculator panel and could not be read.

## What

The calculator shows its result rounded to four decimal places, rounding halves away from zero (0.00005 becomes 0.0001). Four places keep small rates such as 0.0045 readable. Trailing zeros are dropped, so 2.5000 shows as 2.5 and 4.0000 as 4. A short note under the Result label tells the user that results are rounded to 4 decimal places. A result that rounds to zero shows as 0, never as −0. Rounding applies only to the displayed result; the calculation itself keeps full precision until the end. As a safeguard, a very long result wraps inside the panel instead of leaving it.

## Out of scope

Changing which operations are allowed, the size limits, the buttons, or anything about answers, progress and timers. A setting for the number of decimal places.

## Done when

1. 1 ÷ 3 shows 0.3333 and 2 ÷ 3 shows 0.6667.
2. Whole and short results are unchanged: 2 + 3 × 4 shows 14, 0.1 + 0.2 shows 0.3, 2^−2 shows 0.25.
3. A tiny negative result shows 0.
4. Invalid calculations are still rejected with the same messages.
5. The calculator panel states that results are rounded to 4 decimal places.

Checks: `tests/test_calculator.py`, plus a manual look at a calculator-enabled question.
