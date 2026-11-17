# Battle Mode — specified competitive experience

## Why
Offer short, competitive course quizzes separately from non-rewarded Study sessions. Battle rewards performance and high-quality community Battle Decks without affecting learning plans or Study progress.

## What
Battle Mode replaces the former 30-question duel workflow. There must be no user-facing route to create or start a new 30-question duel: every new Battle uses exactly one 15-question Battle Deck. Existing legacy rows are not deleted or retroactively changed by this feature, but they are not selectable for new Play sessions.

The redesigned Battle workflow keeps the existing friend-challenge and mutual random-opponent choices, server-owned timing, 24-hour deadline, saved resumption, answer validation and settlement safeguards unless this specification explicitly changes them.

### Creating a Battle Deck
A Battle Deck is a separate, immutable 15-question snapshot created from one of the creator's own published StudyDuel decks. It is not a second manual authoring form.

1. The creator selects **Create Battle Mode Deck**.
2. The creator selects one of their published source decks, including a reviewed/published deck created manually or through the existing approved AI-/Chatbot-generation workflow.
3. The creator selects exactly 15 distinct questions from that source deck.
4. Before submission, the interface asks for explicit confirmation: **“By submitting, you accept that the deck can be played by everyone.”**
5. After confirmation, the Battle Deck is published and available to other eligible students. There is no separate Battle-Pool opt-in step.

Raw imported Anki source cards and private AI drafts are not Battle Deck sources. They must first complete their existing review and publication workflow. Source-deck edits after submission do not alter the Battle Deck snapshot. To change its questions, the creator makes and submits a new Battle Deck with a new rating history.

Every Battle Deck has exactly 15 valid questions. A source deck with fewer than 15 valid questions is marked not Battle-capable. A source deck with more than 15 questions requires the creator to choose its 15 Battle questions.

### Eligibility and matching
A Battle uses published Battle Decks from the signed-in player's own university. The player chooses one of their enrolled courses; the deck must match that course and a language supported by both participants. A deck creator may participate in a Battle using their own Battle Deck if it is selected, but receives no rating control for that deck.

For a friend challenge, the initiating player chooses the source and, for Top Decks, the specific Battle Deck; the invitee accepts that selection. For a mutual random-opponent match, the initiating selection is authoritative: Random Deck is selected by the server after a compatible match is found, while a chosen Top Deck is shown as the proposed shared deck.

### Battle deck sources
Before a Battle, the initiator chooses one source:

- **Random Deck:** the server chooses one eligible published Battle Deck uniformly at random for the selected university, course and shared language.
- **Top Decks:** the initiator sees the current daily top ten eligible Battle Decks for the selected university, course and shared language and chooses one.

A Battle Deck already contains its frozen 15-card snapshot. Both participants receive those same 15 questions. Existing 30-second per-question timing remains in force. Later source-deck edits, ratings or ranking changes cannot alter an active or completed Battle.

### Daily Top Deck ranking
Each completed Battle participant may rate its selected Battle Deck once, anonymously, using **good**, **neutral** or **bad**. Good contributes `+1`, neutral `0`, and bad `-1` to that Battle Deck's score for the current calendar day in the `Europe/Berlin` time zone (including the MEZ/MESZ changeover). A deck needs at least three ratings on that day to rank. Ties are resolved by the larger number of ratings, then a stable server-side tie-breaker.

Show up to ten ranked decks. If fewer than ten qualify, render the remaining positions as disabled **Outstanding** placeholders. Ratings are visible only as aggregates: the deck creator and other users cannot see which participant supplied a rating.

A participant may submit at most one lifetime rating for a given Battle Deck. A participant who completes their Battle chooses the rating. If they abandon, time out, or otherwise fail to finish, the server automatically records that participant's one neutral rating. It changes neither the daily score nor creator rewards and cannot later be replaced. A creator playing their own Battle Deck receives no rating control; the resulting non-scoring receipt affects neither ratings nor rewards.

### Rewards and progress
Battle uses the existing Game XP, result and streak settlement rules. Game XP and Creator XP both contribute to Total XP, while the profile displays the two components separately: Game XP in blue/violet and Creator XP in green.

A good rating awards the original human creator 5 Creator XP exactly once per participant and Battle Deck. Neutral and bad ratings award no Creator XP. A Battle Deck whose source deck is AI-/Chatbot-generated may be played and ranked after the existing review/publication workflow, but never awards Creator XP, even after a good rating. Creator rewards are separate from Game XP and must be transactional and retry-safe.

Battle must not create or update Study-plan entries, Study progress, learning levels, earned copies, or Study feedback. It uses no Study-mode creator reward logic.

## Out of scope
- Changing the existing AI-/Chatbot-generation, review or publication workflow; Battle only consumes its already published decks.
- Changing Study Mode rules, learning progress, Study Plan or real saved Study sessions.
- Deleting existing legacy duel rows or retroactively changing their saved results.
- Leaderboard design beyond the profile's Game XP, Creator XP and Total XP display.
- Cross-university Battles, moderation workflows, notifications or new social matching rules.

## Done when
1. A creator can form an immutable 15-question Battle Deck from an eligible published source deck only after accepting the public-play confirmation.
2. Battle offers Random Deck and Top Decks after course selection while preserving the existing friend and random-opponent choices.
3. The server selects only published, same-university, same-course, language-compatible Battle Decks. Random selection is uniform; Top Decks follows the daily scoring rule, uses `Europe/Berlin` day boundaries and shows disabled Outstanding placeholders when fewer than ten qualify.
4. Both participants receive the same 15-question snapshot with the existing 30-second question timer. No new 30-question duel can be created or started.
5. Completion enables one anonymous good/neutral/bad rating per participant and Battle Deck. Abandonment, timeout or non-completion writes the one neutral rating automatically. Repeats, retries and reopening cannot create a second rating.
6. Good ratings grant exactly 5 Creator XP once to eligible human creators; AI-/Chatbot-derived Battle Decks, neutral ratings and bad ratings grant none. Existing Game XP and streak rules settle once; all XP types appear correctly in the profile Total XP breakdown.
7. Battle writes do not change Study-plan or Study-progress state. Unauthorized users cannot create/alter another user's Battle Deck, ratings, rewards or Battle.
8. Behavioral Python/UI checks and isolated database checks cover allowed, rejected and restart scenarios, including public consent, snapshot immutability, daily ranking, rating idempotency, reward idempotency and Battle/Study separation. They also confirm that the active Play workflow creates only 15-question Battles.
