# Fifth feature Battle and Study modes

## Why

StudyDuel should support two intentional ways to play. Battle Mode makes a short, competitive round from a community-approved deck and rewards the winner. Study Mode combines material from two students so that each student practises both familiar and unfamiliar questions without turning the activity into an XP competition.

## What

Keep every published deck at exactly 15 cards. This feature changes how cards are selected for a duel; it does not change deck authoring, card validation, or the existing consent and matching rules for friend invitations and mutual random matching.

The Play flow first asks the student to choose one of two modes. The mode is visible in the pre-start summary and is stored with the duel. A completed duel keeps an immutable snapshot of its selected cards, so later changes to pool membership or deck metadata cannot alter an in-progress or completed round. Answer options are shuffled separately for each player.

### Battle Mode

Battle Mode is the competitive mode. It selects one eligible deck at random from the Battle Pool for the agreed course and language. Both players answer the same 15 cards from that selected deck. The existing result rules apply: higher score wins, equal scores draw, and the existing player XP and streak rules apply once when the result is settled.

Only the creator of a published deck may opt that deck into or out of the Battle Pool. Pool membership is separate from publication: a published deck is not placed in the pool by default. A deck is eligible only while it is actively opted in and is compatible with the duel's course and language. Future AI-generated decks are not special here; after their own required review and publication workflow, their creator can opt them into the same pool. This feature does not upload slides, call an AI model, or generate cards.

After a completed Battle Mode duel, each participant gives one anonymous up, neutral, or down rating for the selected deck. A positive rating grants the deck's original creator 5 XP exactly once for that participant and that deck. Neutral and negative ratings grant no creator XP. Repeating a rating, retrying a request, reopening a duel, or playing the same deck again with the same participant must not award creator XP again. Creator XP is separate from the winner's XP and must not change either player's result or streak.

### Study Mode

Study Mode is a non-rewarded learning round. Each participant chooses one eligible published deck for the agreed course and language. The server selects 10 distinct cards from each deck without replacement and combines them into one 20-question shared snapshot. Both students answer the same 20 questions in the same question order. If both choose the same deck, select 20 cards only when the selected content contains 20 distinct cards; because normal decks contain 15 cards, the initial release must instead reject a same-deck Study Mode pairing with an actionable explanation.

Study Mode shows scores and a win, draw, or loss result for feedback, but awards no player XP, no creator XP, and no streak changes. It does not require a deck rating. It still uses the existing server-owned timer, answer validation, abandonment handling, saved progress, privacy, and 24-hour deadline rules unless a later approved specification changes them.

## Data and persistence

Use the existing Supabase project and its published-deck and Play data. Do not create a second database for random decks.

The implementation needs a reviewed database migration that, at minimum:

- records voluntary Battle Pool membership and prevents another user from changing it;
- records the duel mode and supports a 15-card Battle Mode snapshot or a 20-card Study Mode snapshot;
- replaces fixed 30-question validation and cursor limits with mode-aware validation;
- records a participant's Battle Mode rating and enforces one 5-XP creator reward per participant and deck;
- keeps all writes transactional and protected by row-level security and participant checks.

Existing `decks`, `play_duels`, `play_rounds`, `play_queue`, and `play_invites` remain the basis for this feature. Existing published cards stay immutable.

## Out of scope

- Slide upload, AI generation, AI provider selection, model costs, or source-file storage.
- Changing a published deck from 15 cards to another size.
- A separate random-deck database.
- Leaderboard UI changes.
- New matching, friendship, chat, moderation, or notification rules.
- Paying creator XP for Study Mode, for a neutral/down rating, or more than once per participant and deck.

## Done when

1. Play presents Battle Mode and Study Mode with an accurate question count, XP statement, and summary before a duel starts.
2. A deck owner can opt an eligible published deck into and out of the Battle Pool; another student cannot change that choice. Battle Mode selects only an active, compatible pool deck and snapshots exactly 15 cards.
3. A Battle Mode result applies the existing player XP and streak rule exactly once. A positive rating awards the original deck creator 5 XP once per participant and deck; retries and repeat ratings do not duplicate the reward.
4. Study Mode selects exactly 10 distinct cards from each of two different 15-card decks, snapshots exactly 20 cards, and gives both participants the same questions. Same-deck Study Mode is rejected with an actionable explanation.
5. A Study Mode result persists scores and feedback but changes neither player XP/streak nor any creator XP. It requests no rating.
6. Unauthorized users cannot alter pool membership, read another participant's private duel data, submit answers, or create rewards. Rejected actions leave existing data unchanged.
7. Isolated database tests cover pool eligibility, sampling, snapshot size, mode-specific scoring, one-time creator rewards, retry safety, authorization, and a fresh-process reload. Streamlit UI tests cover both selection paths and their rejection states.

## Decisions recorded for implementation

- Published decks always contain 15 cards.
- Battle Mode uses one randomly selected Battle Pool deck and 15 questions.
- Study Mode uses 10 cards from each player's different deck and 20 questions.
- Study Mode gives feedback but no XP, streak progress, creator XP, or rating.
- Battle Mode gives the existing winner XP and 5 creator XP for one positive rating per participant and deck.
