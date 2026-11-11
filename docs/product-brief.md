# StudyDuel product brief

StudyDuel helps students study course material by creating multiple-choice decks, inspecting questions and solutions, and challenging friends or a randomly selected opponent to an asynchronous quiz duel. More correct answers win the duel; completed results award profile XP.

Source: StudyDuel – Gesamtkonzept v2, dated 10 November 2026. This English brief preserves the product rules and separates them from proposed implementation decisions. The original document is retained in docs/source/. All interface labels, documentation, and tests will be in English.

## Delivery decision

The group confirmed the class stack: Python, Streamlit, SQLite, pytest, and uv. Keep app.py for screens, logic.py for rules, db.py for storage, and tests/ for verification. The source's React/Vite/localStorage recommendation and embedded build prompt are not adopted. On 11 November 2026, the user selected real Supabase email/password authentication as the first feature. Review the new acceptance tests before implementation.

Use Supabase Auth for real accounts; opponents remain simulated and server multiplayer remains a later feature. SQLite must preserve accepted changes after stopping and restarting the app. Draft and saved content must remain distinct. The first task is signup, email confirmation, login, and logout. Deck creation follows authentication.

## Navigation and courses

Show StudyDuel, Decks, Play, Leaderboard, and Profile with a profile image. Indicate the active page. Provide back navigation and breadcrumbs for course and deck browsing. The initial courses are Financial Modeling, Corporate Finance, and Investments. How enrollment is chosen is unresolved. Leaderboard design is unresolved; profile XP is its basis.

## Decks and authoring

Each deck belongs to one course and has a name and creator. It contains exactly 15 cards. Every card has a question, exactly four answers, and exactly one correct answer.

Create New Deck opens the course selector, deck name, and card editor. Add Flashcard adds the next card only when the current card is complete. Show progress out of 15. Keep earlier cards accessible for targeted editing and deletion. Save Deck becomes available only when all 15 cards are complete. It opens a mandatory review showing all questions, all answers, and the marked solutions. Back to editing preserves the draft. Create Deck confirms publication.

Users cannot edit or delete a deck after confirmation. Administrative deletion is a separate capability. Stored answer identities must remain meaningful if display order is later shuffled.

Course browsing shows decks with creator and average rating. Opening a deck reveals all 15 questions and solutions deliberately: this is a learning feature. An optional future AI assistant accepts lecture material and places generated questions into the same editable draft and mandatory review workflow; it never bypasses authoring rules.

## Starting and tracking a duel

New Duel selects a friend (searchable list) or random player, then a course, then Random Deck or Top Decks. Random Deck is recommended and selects from all decks in the course. Top Decks selects from the three best average ratings; selection within those three and the fallback for unrated courses are unresolved. Show a summary before Start Duel.

The challenger answers first. Both participants receive the same deck and question order, but answer order is shuffled separately for each player. Duels are asynchronous, never labeled Live.

Play groups the current user's duels into:
- Ongoing: the user is due to play, with remaining time, Play, and Decline only for received challenges.
- Pending: the user has played and waits for the opponent; show their own score and remaining time.
- Completed: both played or the deadline expired. Reveal opponent results only here. Clearly label win, draw, or loss with text and symbols. A timeout result says the opponent did not play instead of inventing their score.

## Answering and reviewing

Each of 15 questions has a 30-second countdown. A correct answer scores 1; a wrong or expired answer scores 0. Response speed is not a tie-breaker. Display four answers in a 2-by-2 layout and question progress with symbols as well as color. Reveal the correct answer after a response; mark a wrong selected answer separately. On expiry, say Time expired, reveal the correct answer, and continue.

Exit, tab changes, and profile navigation during a round require the same confirmation: confirming ends the round as a loss; canceling stays in the round. After question 15, say Your round is finished and show the user's score. Require an anonymous up/neutral/down rating before navigating away, even if the user previously rated that deck. The round then becomes Pending or Completed. Exact deadline start and the distinction between answer completion and rating completion need agreement.

Profile history lists newest duels first, with date, result, score, percentage, and Review. Review shows all 15 questions, the user's answers, correct answers, and outcomes. Each question has Report with a confirmation. Cancel writes nothing; confirm stores the report and permanently shows Reported for that user and question. A person may report a question once.

## Scoring and profile

Higher scores win; equal scores draw. These rules apply to friends and random opponents.
- Wins 1–3 in a streak award 40 XP each.
- The fourth and subsequent consecutive wins award 80 XP each.
- Winning because the opponent did not play in time awards the same win XP.
- A draw awards 0 XP and resets the streak.
- A loss, confirmed round abandonment, or not playing within 24 hours deducts 10 XP and resets the streak.
- Declining a challenge changes neither XP nor streak and produces no win/loss result.
- XP never falls below zero. Duel points and XP remain separate.

After three consecutive wins, show Next win counts double. Persist results and apply XP once per result, including after a restart (proposed consistency requirement derived from these scoring rules).

## Ratings, moderation, friends, and extensions

Show only aggregate deck ratings. The numerical mapping for up/neutral/down, ranking ties, and rounding require a decision. Each completed played round requires a rating; repeating a deck does not waive it.

At 20 reports a deck enters the admin view for keep/delete review. Reports target questions, but whether this threshold sums reports across a deck or applies to one question is unresolved. Only an admin-role user may access moderation. Behavior of existing duels after administrative deck deletion is unresolved.

Friend search appears in Profile and New Duel. Direct friendship versus requests, rejection, and removal are open decisions. Random-opponent eligibility and rejection behavior are also open.

Calendar reminders cover an incoming duel's 24-hour deadline and recurring study. The prototype may offer a downloadable calendar event; real Google/Apple integrations are later. Timing, frequency, and opt-out are open. AI lecture upload, supported formats, and question generation count are also open.

## Proposed delivery sequence

1. Supabase authentication, then manual deck authoring, review, durable confirmation, and read-only browsing.
2. Timed answering and required ratings.
3. Simulated challenges, state transitions, and deadlines.
4. XP, streaks, history, review, and reports.
5. Friends and leaderboard once their rules are agreed.
6. Optional admin moderation, calendar export, and AI generation.

Use deterministic opponent outcomes and an injectable clock for tests and prototype controls. Clearly distinguish simulation controls from real multiplayer.

## Confirmed account and profile scope

Authentication and profile setup are now the first workflow. See docs/profile-requirements.md for required username, university, course and language selections, editable photo/avatar options, visibility decisions, and Supabase persistence. XP, streak, and friends are displayed with initial empty values; their gameplay and management rules remain later work. These decisions supersede demo-only profile assumptions above.
