# Battle Mode implementation task

Parent feature: [Battle Mode](../battle-mode.md).

## Why
Implement the approved competitive Battle workflow without changing Study rules, Study progress, historic classic duels or production data outside an additive reviewed migration.

## What
Build the implementation in reviewed slices on a `feature/battle-mode-implementation` branch created from current `main`. Keep screen rendering in `app.py`, rule validation/sampling/ranking helpers in `logic.py`, and Supabase calls in `db.py`.

### Player flow
1. From Play, choose **Battle Mode**.
2. The university is the signed-in player's university; the player selects one of their enrolled courses.
3. Choose **Random Deck** or **Top Decks**.
4. Keep the existing friend challenge and mutual random-opponent paths. A Battle starts only when the selected deck language is supported by both participants.
5. The server validates eligibility, chooses/freezes 15 distinct cards, and creates one shared Battle snapshot.
6. Both participants answer the snapshot using the existing 30-second question timer, persistence, deadline, answer validation and restart/resume behavior.
7. The existing once-only Game XP and streak settlement runs. Battle writes must not create Study progress or Study-plan effects.
8. A completed participant submits one anonymous `good`, `neutral` or `bad` rating. A non-completing participant receives one automatic neutral rating. The original human creator receives 5 Creator XP only for a good rating.

### Required persistent state
Use an additive migration; do not rewrite applied schema files or historical rows. The design must durably record:
- duel mode and a frozen 15-card Battle snapshot;
- source type (`random` or `top`), selected deck, university, course and language;
- Battle eligibility for a published deck, including at least-15-card validation;
- one rating receipt per participant and deck, including automatic neutral receipts;
- daily rating aggregates keyed by the `Europe/Berlin` calendar day;
- idempotent Creator XP awards and whether a deck is AI-generated; and
- separate Game XP and Creator XP profile components while preserving Total XP and legacy values.

The database must enforce participant-only actions, one rating receipt per participant/deck, creator-only eligibility changes where applicable, and retry-safe XP writes. It must use server-owned identity and transactions rather than UI checks.

### Required UI states
- Random Deck has an accurate empty state when no eligible deck exists.
- Top Decks presents up to ten selectable decks ranked by the parent specification. Missing qualifying places are disabled and labelled **Outstanding**.
- Decks with fewer than 15 questions are clearly marked as not Battle-capable.
- The profile shows Total XP plus a small blue/violet Game XP and green Creator XP breakdown.
- A deck's creator may play their own selected deck, but receives no rating control for it; that non-scoring receipt cannot affect rating totals or Creator XP.
- Existing classic 30-question history/review screens remain distinguishable from new Battle results.

### Required behavior before coding
Review these scenarios with the group and turn them into tests before implementation:
- **Allowed:** A student selects a course and a compatible eligible published deck is sampled uniformly by Random Deck.
- **Allowed:** A 100-question deck contributes 15 distinct frozen cards; a 15-question deck contributes all cards.
- **Allowed:** Top Decks ranks daily good/neutral/bad scores and shows fewer than ten cards with Outstanding placeholders.
- **Rejected:** A deck with fewer than 15 cards, the wrong university/course, or an unsupported language cannot start a Battle.
- **Rejected:** A user cannot alter another user's rating, rate the same deck twice, obtain duplicate Creator XP, or create Study progress through Battle.
- **Automatic:** Abandonment, timeout or non-completion creates exactly one neutral receipt and no Creator XP.
- **Restart:** A fresh process reopens an active Battle with the same card snapshot and progress; settlement and Creator XP remain once-only after retries.
- **Regression:** Existing classic duels retain 30-question validation, historical results and review behavior.

## Out of scope
Implementing AI generation itself, modifying Study Mode, changing historic classic-duel outcomes, redesigning the leaderboard, adding cross-university Battles, notifications, moderation or a merge into `main`.

## Done when
1. The implementation follows the parent specification and all listed scenarios have reviewed expected outcomes.
2. New behavioral Python/UI tests and isolated database tests pass alongside existing Play and Study regression coverage.
3. The Supabase migration is reviewed for row-level security, idempotency, legacy compatibility and mode-aware Study-progress exclusion.
4. A manual two-participant Battle, rejection case and full restart are recorded in [Battle Mode verification](../../docs/battle-mode-verification.md).
5. A reviewed pull request is ready for `main`; no release or merge occurs without group approval.
