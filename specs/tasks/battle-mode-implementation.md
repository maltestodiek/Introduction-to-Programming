# Battle Mode implementation task

Parent feature: [Battle Mode](../battle-mode.md).

## Why
Implement the approved Battle Deck workflow: creators turn their reviewed published learning decks into public, immutable 15-question competitive decks. Retire the former 30-question duel workflow from active Play and keep Battle completely separate from Study progress.

## What
Build the implementation in reviewed slices on a `feature/battle-mode-implementation` branch created from current `main`. Keep screen rendering in `app.py`, rule validation/sampling/ranking helpers in `logic.py`, and Supabase calls in `db.py`. Do not delete existing legacy data without a separately reviewed migration.

### Player and creator flow
1. A creator opens **Create Battle Mode Deck** and selects one of their own published source decks.
2. The creator chooses exactly 15 distinct valid questions.
3. Before saving, the creator explicitly accepts: **“By submitting, you accept that the deck can be played by everyone.”**
4. The system saves an immutable, public Battle Deck snapshot. Source-deck edits cannot change it.
5. A Battle initiator chooses their enrolled course and Random Deck or Top Decks, then uses the existing friend challenge or mutual random-opponent route.
6. Random Deck chooses an eligible published Battle Deck uniformly after a compatible match; Top Decks lets the initiator choose a ranked Battle Deck.
7. Both participants answer the same 15 frozen questions using the existing 30-second timer and durable resume/deadline behavior.
8. Existing Game XP/streak settlement runs once. Completion permits one rating; non-completion writes one automatic neutral receipt. Battle never changes Study plan or progress.

Raw imported Anki source cards and private AI drafts cannot be used directly. A source deck may be manually authored or AI-/Chatbot-generated, but it must have completed its existing review and publication process. An AI-/Chatbot-derived Battle Deck never earns Creator XP.

### Required persistent state
Use an additive migration; do not rewrite applied schema files or historical rows. The design must durably record:
- a creator-owned public Battle Deck, source deck/version, university, course, language and immutable 15-question snapshot;
- submission/public-play consent;
- duel mode, source type (`random` or `top`) and selected Battle Deck;
- one rating receipt per participant and Battle Deck, including automatic neutral and own-deck non-scoring receipts;
- daily rating aggregates keyed by the `Europe/Berlin` calendar day;
- source origin needed to suppress Creator XP for AI-/Chatbot-derived Battle Decks;
- idempotent Game XP and Creator XP settlement; and
- separate Game XP and Creator XP profile components while preserving Total XP and legacy values.

The database must enforce creator-only Battle Deck creation, participant-only Battle actions, one rating receipt per participant/deck, public-consent capture, and retry-safe XP writes. It must use server-owned identity and transactions rather than UI checks.

### Required UI states
- A source deck with fewer than 15 valid questions is marked not Battle-capable.
- The source-deck selector excludes another user's decks, raw imports and private AI drafts.
- Random Deck has an accurate empty state when no eligible Battle Deck exists.
- Top Decks presents up to ten selectable Battle Decks ranked by the parent specification. Missing qualifying places are disabled and labelled **Outstanding**.
- The profile shows Total XP plus a small blue/violet Game XP and green Creator XP breakdown.
- A creator may play their own selected Battle Deck, but receives no rating control for it; its non-scoring receipt cannot affect rating totals or Creator XP.
- No active Play screen offers a 30-question duel; every new Battle clearly shows its 15-question format.

### Required behavior before coding
Review these scenarios with the group and turn them into tests before implementation:
- **Allowed:** A creator selects exactly 15 questions from their own published 100-question source deck, accepts public-play consent and creates an immutable Battle Deck.
- **Allowed:** A reviewed/published AI-/Chatbot source deck becomes a playable Battle Deck but never produces Creator XP.
- **Allowed:** A student selects a course and a compatible eligible Battle Deck is selected uniformly by Random Deck.
- **Allowed:** Top Decks ranks daily good/neutral/bad scores and shows fewer than ten decks with Outstanding placeholders.
- **Rejected:** A source deck with fewer than 15 questions, another user's source deck, a raw import, a private AI draft, missing consent, another university/course, or an unsupported language cannot start/create a Battle.
- **Rejected:** A user cannot alter another user's Battle Deck or rating, rate the same Battle Deck twice, obtain duplicate Creator XP, or create Study progress through Battle.
- **Automatic:** Abandonment, timeout or non-completion creates exactly one neutral receipt and no Creator XP.
- **Restart:** A fresh process reopens an active Battle with the same Battle Deck snapshot and progress; settlement and Creator XP remain once-only after retries.
- **Regression:** The active Play workflow can create only 15-question Battles; existing legacy rows remain untouched by the additive migration.

## Out of scope
Implementing AI generation itself, modifying Study Mode, deleting legacy duel data or changing historic outcomes, redesigning the leaderboard, adding cross-university Battles, notifications, and an immediate merge into `main`.

## Done when
1. The implementation follows the parent specification and all listed scenarios have reviewed expected outcomes.
2. New behavioral Python/UI tests and isolated database tests pass alongside existing Play and Study regression coverage.
3. The Supabase migration is reviewed for row-level security, consent capture, idempotency, legacy compatibility and mode-aware Study-progress exclusion.
4. A manual two-participant Battle, rejection case and full restart are recorded in Battle Mode verification notes.
5. A reviewed pull request is ready for `main`; no release or merge occurs without group approval.
