# Immersive round interface

Parent topics: [Appearance and navigation](../appearance-and-navigation.md), [Battle Mode](../battle-mode.md) and [Study Mode and learning progress](../study-mode.md). Builds on [Battle round layout](battle-round-layout.md) and [Study round layout](study-round-layout.md).

## Why

Battle and Study rounds presented questions like a form. A game-like round — a start countdown, lively answer feedback and a visible streak — keeps students engaged without changing any rule of play.

## What

**Start countdown.** Starting a new Battle or Study session shows 3, 2, 1, Best of Luck!, then Go! in the main panel using the active theme. Keep the sidebar visible. Fetch the first question after the intro so Battle keeps its full answer time. All resume paths skip the intro, even with zero answers. Existing question screens and feedback keep their layout.

**Answer feedback.** A correct chosen answer pops with a green glow, a small confetti burst and, in Battle only, a rising "+XP" chip. A wrong answer keeps its shake and adds a brief red edge vignette, while the correct answer pulses once so the eye finds it. The overview tile of the just-answered question flashes as it takes its colour.

**Streak.** From two correct answers in a row, a flame badge with the current run appears beside the Overview heading in the side panel. Reaching 3, 5 or 10 in a row shows a short banner (On fire! / Unstoppable! / Legendary!). The streak is computed from the round's already-loaded answers, adds no state or persistence and never changes XP or scoring.

**Equal card heights.** Answer fields match the question card's height (110px desktop, 96px narrow screens) both while answering and in feedback, so the layout does not jump between states and the timer and Continue control stay visible without scrolling on a laptop screen.

**Leaving a Battle.** The Leave control is a red gradient pill. It opens a centred confirmation card over a dimmed round — not a dropdown — with Keep fighting and Leave Battle; leaving still uses the server-authoritative abandonment action, and the timer keeps running while the card is open.

**Overview panel.** The Overview heading carries a live accuracy chip (percent correct of answered questions) from the first answer on. Below the tile grid sit the streak badge and a five-segment combo meter that fills with the current streak, empties on a wrong answer and, in Battle only, glows while full. All of it is derived from the round's loaded answers.

**Battle review.** The review dialog shows the result as one clickable tile grid: each tile opens that question below, with the student's answer and the correct answer marked, replacing the fifteen expanders. Reporting a question stays available on the opened question.

**Atmosphere.** Each question card slides in briefly. The Battle timer bar turns orange at 15 seconds and red with a pulse at 5. The Battle rating screen pops the final score in and shows confetti for a strong round (8+ correct).

All motion is decorative, times out on its own and is disabled under reduced-motion preferences.

## Out of scope

Sound. Changing question order, timing rules, scoring, XP, levels, persistence or any database rule. The classic 30-question duel screen.

## Done when

1. Allowed: answering, continuing, leaving, rating and resuming a round work exactly as before; a resumed Battle round starts without a countdown and with the server's remaining time.
2. Rejected: the countdown cannot be clicked through to answer early, and no animation element intercepts clicks on answers or controls.
3. Restart: after a new sign-in a running round resumes directly at its current question; streak and tiles rebuild from the saved answers.
4. The countdown, feedback effects, accuracy chip, streak badge, combo meter and equal 110px/96px card heights appear in both Battle and Study rounds, and all effects are off under `prefers-reduced-motion`.
5. In the Battle review, every question remains reachable (one click per tile), its report action still works, and the shown score equals the stored answers.

Checks: `tests/test_round_effects.py`, `tests/test_battle_ui.py`, `tests/test_study_round_ui.py`, plus a manual look at a Battle and a Study round.
