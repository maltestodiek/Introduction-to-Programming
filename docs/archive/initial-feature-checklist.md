# StudyDuel feature checklist

Planned features, not implemented. Use English and the class stack: Python, Streamlit, SQLite, pytest, and uv. Use demo users and simulated opponents for the local prototype.

## Core features in proposed build order

- [ ] Navigation: Decks, Play, Leaderboard, Profile, active-page indication, and back navigation.
- [ ] Courses and browsing: Financial Modeling, Corporate Finance, Investments; deck names, creators, ratings, and visible questions and solutions.
- [ ] Manual deck creation: course and name, exactly 15 questions, four answers per question, and exactly one correct answer.
- [ ] Draft editing: edit or delete any card before confirmation; validate completeness and card count.
- [ ] Mandatory review and confirmation: inspect all solutions before saving; confirmed decks cannot be edited or deleted by users.
- [ ] Persistent decks: save to SQLite and reopen after a full process restart.
- [ ] Quiz round: 30 seconds per question, shuffled answer choices, immediate feedback, symbols and progress, one point per correct answer.
- [ ] Exit confirmation: cancel stays in the round; confirmed abandonment counts as a loss.
- [ ] Mandatory rating: up, neutral, or down after every completed round; display aggregate ratings only.
- [ ] New duel: friend or random opponent, course, and random or top-rated deck.
- [ ] Duel dashboard: Ongoing, Pending, Completed; decline received challenges; show remaining time; reveal opponent results only when completed.
- [ ] Deadline: apply the 24-hour rule, with deterministic simulation controls for the prototype.
- [ ] Results and XP: compare correct answers; draws explicit; 40 XP for a win, 80 from the fourth consecutive win; loss deducts 10 with a floor of zero.
- [ ] Streaks: loss or draw resets the streak; declining preserves XP and streak.
- [ ] Profile and history: name, image, XP, streak, newest duels first, scores, dates, and percentages.
- [ ] Learning review and reports: own and correct answers for all questions; report confirmation; one report per person per question.
- [ ] Friends: search and friendship management; settle request/removal rules before building.
- [ ] Leaderboard: rank by XP; settle ranking and tie rules before building.

## Optional extensions

- [ ] Admin review of reported decks; resolve report threshold aggregation.
- [ ] Calendar reminders or downloadable calendar entries.
- [ ] AI-generated draft questions from lecture uploads, using the same mandatory review.

## Verification for each workflow

Accepted changes survive a restart. Rejected actions leave saved data unchanged. Review expected test outcomes before implementation. Keep player progress separate from deck content.

First implementation scope: specs/first-feature.md. Full rules and unresolved decisions: docs/product-brief.md and docs/verification-proposal.md. Real login and online multiplayer are outside the local class prototype.
