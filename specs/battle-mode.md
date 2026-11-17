# Battle Mode — specified competitive experience

## Why
Offer short, competitive course quizzes separately from non-rewarded Study sessions. Battle rewards performance and high-quality community decks without affecting learning plans or Study progress.

## What
Battle Mode is a new workflow beside Study Mode. The earlier classic 30-question duel engine remains historical and must continue to display its saved rounds, reviews and scores unchanged. The redesigned workflow keeps the existing friend-challenge and mutual random-opponent choices, server-owned timing, 24-hour deadline, saved resumption, answer validation and settlement safeguards unless this specification explicitly changes them.

### Eligibility and matching
A player battles only within their own university. The player chooses a course; the selected Battle deck must match that course and a language supported by both participants. Eligible decks are published decks at that university with at least 15 valid questions. Decks with fewer than 15 questions are shown as not Battle-capable and cannot be selected.

A deck's creator may participate in a Battle using their own deck if it is selected. This is an accepted consequence of the random selection; it must not give that creator rating privileges.

### Battle deck sources
Before a Battle, the player chooses one source:

- **Random Deck:** the server chooses one eligible published deck uniformly at random for the selected university, course and shared language. It then selects 15 distinct cards from that deck without replacement. A 15-card deck therefore supplies all of its cards. The selected cards are frozen in the Battle snapshot.
- **Top Decks:** the player sees the current daily top ten eligible decks for the selected university, course and shared language and chooses one. The server samples and freezes 15 distinct cards in the same way.

Each Battle has one shared 15-question snapshot; both participants receive the same questions. Existing 30-second per-question timing remains in force. Later deck edits, ratings or ranking changes cannot alter an active or completed Battle.

### Daily Top Deck ranking
Each completed Battle participant may rate its selected deck once, anonymously, using **good**, **neutral** or **bad**. Good contributes `+1`, neutral `0`, and bad `-1` to that deck's score for the current calendar day in the `Europe/Berlin` time zone (including the MEZ/MESZ changeover). A deck needs at least three ratings on that day to rank. Ties are resolved by the larger number of ratings, then a stable server-side tie-breaker.

Show up to ten ranked decks. If fewer than ten qualify, render the remaining positions as disabled **Outstanding** placeholders. Ratings are visible only as aggregates: the deck creator and other users cannot see which participant supplied a rating.

A player may submit at most one lifetime rating for a given deck. A participant who completes their Battle chooses the rating. If they abandon, time out, or otherwise fail to finish, the server automatically records that participant's one neutral rating. It changes neither the daily score nor creator rewards and cannot later be replaced.

### Rewards and progress
Battle uses the existing Game XP, result and streak settlement rules. Game XP and Creator XP both contribute to Total XP, while the profile displays the two components separately: Game XP in blue/violet and Creator XP in green.

A good rating awards the original human deck creator 5 Creator XP exactly once per participant and deck. Neutral and bad ratings award no Creator XP. AI-generated decks never award Creator XP, even after a positive rating. Creator rewards are separate from Game XP and must be transactional and retry-safe.

Battle must not create or update Study-plan entries, Study progress, learning levels, earned copies, or Study feedback. It uses no Study-mode creator reward logic.

## Out of scope
- Slide upload, AI provider selection, AI deck generation and source-file storage.
- Changing Study Mode rules, learning progress, Study Plan or real saved Study sessions.
- Changing historical classic-duel snapshots, results or scores.
- Leaderboard design beyond the profile's Game XP, Creator XP and Total XP display.
- Cross-university Battles, moderation workflows, notifications or new social matching rules.

## Done when
1. Battle offers Random Deck and Top Decks after course selection while preserving the existing friend and random-opponent choices.
2. The server selects only published, same-university, same-course, language-compatible Battle-capable decks and freezes exactly 15 distinct cards for each Battle.
3. Random selection is uniform across eligible decks. Top Decks display the daily top ten by the specified scoring rule, use `Europe/Berlin` day boundaries and show disabled Outstanding placeholders when fewer than ten qualify.
4. Both participants receive the same 15-question snapshot with the existing 30-second question timer. Historic 30-question classic duels remain readable and playable as before.
5. Completion enables one anonymous good/neutral/bad rating per participant and deck. Abandonment, timeout or non-completion writes the one neutral rating automatically. Repeats, retries and reopening cannot create a second rating.
6. Good ratings grant exactly 5 Creator XP once to eligible human creators; AI-generated decks, neutral ratings and bad ratings grant none. Existing Game XP and streak rules settle once; all XP types appear correctly in the profile Total XP breakdown.
7. Battle writes do not change Study-plan or Study-progress state. Unauthorized users cannot change deck eligibility, ratings, rewards or another participant's Battle.
8. Behavioral Python/UI checks and isolated database checks cover allowed, rejected and restart scenarios, including sampling, daily ranking, rating idempotency, reward idempotency and Battle/Study separation. Existing Play regression checks remain green.
