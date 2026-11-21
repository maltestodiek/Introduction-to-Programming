# Battle Mode — specified competitive experience

## Why
Offer short, competitive course quizzes separately from non-rewarded Study sessions. Battle rewards performance and high-quality community Battle Decks without affecting learning plans or Study progress.

## What
Battle Mode replaces the former 30-question duel workflow. There must be no user-facing route to create or start a new 30-question duel: every new Battle uses exactly one 15-question Battle Deck. Existing legacy rows are not deleted or retroactively changed by this feature, but they are not selectable for new Play sessions.

Random opponents play asynchronously. The server persists the deck, answers, search deadline and each player's finish deadline. Leaving saves progress, and reopening the app offers Resume in Active battles. The 30-second question clock continues while away.

### Creating a Battle Deck
A Battle Deck is a separate, immutable 15-question snapshot created from one of the creator's own published UniArena decks. It is not a second manual authoring form.

1. The creator selects **Create Battle Mode Deck**.
2. The creator selects one of their published source decks from a dropdown, including a reviewed/published deck created manually or through the existing approved AI-/Chatbot-generation workflow. The question list appears only after that selection.
3. The creator selects exactly 15 distinct questions from that source deck. A submit attempt with any other count opens a clear prompt that exactly 15 questions are required.
4. Before submission, the interface asks for explicit confirmation: **“By submitting, you accept that the deck can be played by everyone.”**
5. After confirmation, the Battle Deck is published and available to other eligible students. There is no separate Battle-Pool opt-in step.

A shortcut starts the same flow from a Study deck: the page of one of the creator's own Study decks shows a large **Publish as Battle deck** button with a Battle icon. It opens **Create Battle Mode Deck** with that deck already chosen as the source, so the creator goes straight to choosing 15 questions; a **Back to Study deck** button returns without creating anything. Shared Study copies and legacy decks do not show the button. With fewer than 15 questions the button is disabled and the page states how many questions the deck has. The Study deck itself is not changed.

Raw imported Anki source cards and private AI drafts are not Battle Deck sources. They must first complete their existing review and publication workflow. Source-deck edits after submission do not alter the Battle Deck snapshot. To change its questions, the creator makes and submits a new Battle Deck with a new rating history.

Every Battle Deck has exactly 15 valid questions. A source deck with fewer than 15 valid questions is marked not Battle-capable. A source deck with more than 15 questions requires the creator to choose its 15 Battle questions.

### Eligibility and matching
A Battle uses published Battle Decks from the signed-in player's own university. The player chooses one of their enrolled courses; the deck must match that course and a language supported by both participants. A deck creator may participate in a Battle using their own Battle Deck if it is selected, but receives no rating control for that deck.

Before a Random Deck search or invitation is created, the server confirms that at least one eligible public Battle Deck already exists for the selected university, course and language. If none exists, matchmaking is unavailable and the player receives clear feedback instead of a pending search. A random opponent search opens the first question immediately. The server pairs the oldest compatible opt-in immediately or freezes an eligible deck and searches for up to 48 hours from entry. A requested Top Deck must match the frozen deck. Both players answer the same questions. Each has one hour from opening their own first question. An unopened random entry is released after one hour. An accepted friend invitation retains its 24-hour window to open the first question.

An unfinished, unmatched entry expires without a loss or XP. A finished, unmatched round stays eligible for the rest of the original 48 hours. If a matched participant misses their deadline, that player forfeits. Settle scores and XP exactly once when both finish or a matched deadline decides the outcome. Identical missed deadlines leave both participants with a loss. The dashboard groups accepted and random rounds under **Active battles**, unanswered friend invitations under **Battle invitations**, and settled scores and XP under **Recent results**.

### Battle deck sources
Before a Battle, the initiator chooses one source:

- **Random Deck:** the server chooses one eligible published Battle Deck uniformly at random for the selected university, course and shared language.
- **Top Decks:** the initiator sees the current top ten eligible Battle Decks by their lifetime rating score for the selected university, course and shared language and chooses one.

A Battle Deck already contains its frozen 15-card snapshot. Both participants receive those same 15 questions. Existing 30-second per-question timing remains in force. Later source-deck edits, ratings or ranking changes cannot alter an active or completed Battle.

### Lifetime Top Deck ranking
Each completed Battle participant may rate its selected Battle Deck once, anonymously, using **good**, **neutral** or **bad**. Good contributes `+1`, neutral `0`, and bad `-1` to that Battle Deck's lifetime score. Every eligible Battle Deck ranks immediately; a deck without a rating has a score and rating count of zero. Ties are resolved by the larger number of lifetime ratings, then a stable server-side tie-breaker.

Show up to ten ranked decks. If fewer than ten eligible decks exist, render the remaining positions as disabled **Outstanding** placeholders. Ratings are visible only as aggregates: the deck creator and other users cannot see which participant supplied a rating.

A participant may submit at most one lifetime rating for a given Battle Deck. A participant who completes their Battle chooses the rating. If they abandon, time out, or otherwise fail to finish, the server automatically records that participant's one neutral rating. It changes neither the lifetime score nor XP and cannot later be replaced. A creator playing their own Battle Deck receives no rating control; the resulting non-scoring receipt affects neither ratings nor XP.

### Rewards and progress
Battle uses the existing Battle XP, result and streak settlement rules. Battle XP is the only XP shown in the profile and is the sole value used by the leaderboard.

Ratings affect only the lifetime Top Deck score. Good, neutral and bad ratings never award XP to a deck creator or participant, regardless of source origin.

Battle must not create or update Study-plan entries, Study progress, learning levels, earned copies, or Study feedback.

## Out of scope
- Changing the existing AI-/Chatbot-generation, review or publication workflow; Battle only consumes its already published decks.
- Changing Study Mode rules, learning progress, Study Plan or real saved Study sessions.
- Deleting existing legacy duel rows or retroactively changing their saved results.
- Leaderboard design beyond the profile's Battle XP display.
- Cross-university Battles, moderation workflows, notifications or new social matching rules.

## Done when
1. A creator can form an immutable 15-question Battle Deck from an eligible published source deck only after accepting the public-play confirmation.
2. Battle offers Random Deck and Top Decks after course selection while preserving the existing friend and random-opponent choices.
3. The server selects only published, same-university, same-course, language-compatible Battle Decks. Random selection is uniform; Top Decks follows the lifetime scoring rule and shows disabled Outstanding placeholders when fewer than ten qualify.
4. Both participants receive the same 15-question snapshot with the existing 30-second question timer. No new 30-question duel can be created or started.
5. Completion enables one anonymous good/neutral/bad rating per participant and Battle Deck. Abandonment, timeout or non-completion writes the one neutral rating automatically. Repeats, retries and reopening cannot create a second rating.
6. Ratings change only lifetime Top Deck scoring and never award XP. Existing Battle XP and streak rules settle once; Battle XP appears correctly in the profile and leaderboard.
7. Battle writes do not change Study-plan or Study-progress state. Unauthorized users cannot create/alter another user's Battle Deck, ratings, rewards or Battle.
8. Behavioral Python/UI checks and isolated database checks cover allowed, rejected and restart scenarios, including public consent, snapshot immutability, lifetime ranking, rating idempotency, reward idempotency and Battle/Study separation. They also confirm that the active Play workflow creates only 15-question Battles.


## Implementation and verification basis
Implement Battle in a dedicated feature branch. Keep Streamlit screens in `app.py`, selection/ranking validation in `logic.py`, and Supabase access in `db.py`. Use an additive database migration: do not delete existing legacy rows or rewrite applied SQL files.

The durable state must include the public Battle Deck snapshot and its source/version, public-play consent, selected source (`random` or `top`), one rating receipt per participant and Battle Deck, lifetime rating aggregates, and idempotent Battle XP settlement.

Before code is written, translate these required scenarios into behavioral Python/UI checks and isolated database checks:

- A creator can choose exactly 15 questions from their own published source deck, accept public-play consent, and create an immutable Battle Deck.
- A reviewed/published AI-/Chatbot source deck may create a Battle Deck and is rated by the same lifetime-ranking rules.
- Random Deck selects uniformly from eligible Battle Decks; Top Decks ranks lifetime scores and renders Outstanding placeholders.
- Another user's source deck, a raw import, a private AI draft, fewer than 15 questions, missing consent, a different university/course, or an unsupported language is rejected without saved changes.
- A participant cannot rate twice, alter another participant's rating, receive rating XP, or create Study progress through Battle.
- Abandonment, timeout or other non-completion stores exactly one neutral receipt and no XP.
- After a full application/process restart, an active Battle resumes with the same 15-question snapshot and progress; later retries cannot settle Battle XP twice.
- The active Play workflow creates only 15-question Battles.

Run focused Python/UI tests, isolated database tests, and existing shared regression tests. Manually verify a two-participant Battle, a rejection path and a full restart before any merge. Record commands, results and remaining manual limitations in the pull request.
