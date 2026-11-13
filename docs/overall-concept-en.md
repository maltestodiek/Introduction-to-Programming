# StudyDuel Overall Concept v2

10 November 2026 · @Penelope

Current implementation: Python, Streamlit and Supabase. No React frontend or browser-only database is being built. This English translation preserves the original concept’s historical technology proposal in a clearly marked reference section; it is not the active implementation plan.

## Overview

StudyDuel is a learning app where students create quiz decks for their courses and challenge each other to duels. It combines flashcard learning, as in Anki, with competition among friends, as in Quizduell. Whoever answers more questions correctly wins the duel and earns XP.

Navigation: StudyDuel appears at the top left; Decks, Play and Leaderboard are in the centre; Profile and the profile picture are at the top right. Colour highlights the active tab.

Prototype courses: Financial Modeling, Corporate Finance and Investments.

- **Course:** A university subject, such as Corporate Finance. Each deck belongs to exactly one course.
- **Deck:** Exactly 15 quiz cards created by a user, for example “Corporate Finance 1”.
- **Card:** A question with exactly four possible answers, exactly one of which is correct.
- **Duel:** Two players take turns answering the same 15 questions from the same deck.
- **Opponent:** A friend from the friends list or a randomly selected player.
- **Points:** Count within a duel. Each correct answer earns one point. Points determine the winner.
- **XP:** Profile experience points awarded after each duel; the basis for the leaderboard.
- **Win streak:** Consecutive wins. Starting with the fourth consecutive win, XP awards double.
- **Report:** A report about an individual question that is incorrect or faulty.

## Decks page

The Decks page has two sections: “+ Create New Deck” at the top and a course overview for browsing existing decks below.

### Create New Deck

Clicking the plus sign and “Create New Deck” opens an editor arranged from top to bottom:

1. **Course:** A dropdown with Financial Modeling, Corporate Finance and Investments.
2. **Deck name:** A free-text field, for example “Corporate Finance 1”.
3. **Questions 1 to 15:** Each card has a Question field and Answer 1 to Answer 4 fields. Questions are added using a fixed input value. A selection circle to the left of each answer marks the correct answer. Only one answer can be selected at a time.
4. **+ Add Flashcard:** Adds the next card. A counter shows progress, for example “Card 7 of 15”.
5. **Card list:** Every card created so far remains visible. Any earlier card can be selected, edited or individually deleted, not just the last card.
6. **Save Deck:** Becomes active only when all 15 cards are complete.
7. **Review overview:** After Save Deck, all 15 questions, their answers and marked solutions appear for checking. The question “Create the deck like this?” offers “Back to editing” and “Create Deck”. Back to editing returns to the card list, where every card can be changed.

Creation rules:

- A new card can be added only when the current card has a question, all four answers and a selected correct answer.
- A deck contains exactly 15 cards.
- Before submission, every card can be edited or deleted. After creation, a deck can neither be edited nor deleted. The review overview is therefore mandatory.
- Answers are shuffled during play, regardless of where the correct answer was originally entered.

### Create decks with an AI assistant as an extension

Alongside manual entry, a chatbot provides a second way to create questions from lecture material:

1. The user chooses a course and deck name and uploads a lecture, such as Corporate Finance slides.
2. The chatbot automatically generates multiple-choice questions with four answers and a marked solution each.
3. The questions enter the normal card list. The user reviews them, edits them if necessary, and submits them through the review overview.

This makes deck creation easier. All manual-creation rules still apply, especially mandatory review before submission.

### Course overview and viewing decks

Below Create New Deck are the courses in which the user is enrolled. Navigation has three levels:

1. Choose a course, for example Corporate Finance.
2. See its deck list, including deck name, creator and average rating, based on thumbs up, neutral and thumbs down.
3. Open a deck, such as Corporate Finance 1, to see all 15 questions, all four answers and the marked correct answer.

A breadcrumb at the top shows the location, for example Decks > Corporate Finance > Corporate Finance 1, with a Back button.

Deliberate decision: All decks and solutions can be viewed freely. This is intentional in a learning app: looking at a deck beforehand is itself a way to learn.

## Play page

The Play page is the Game Overview. A “+ New Duel” button appears at the top right. Three columns below group the user's duels by status.

### Game Overview

**Ongoing:** It is your turn, for example because somebody challenged you. A card shows course, deck name, opponent and “Your turn · 18 hours left”, with Play and Decline buttons.

**Pending:** You have played, but the opponent has not. A card shows course, deck name, opponent and “Your score: 10/15 (67%) · Waiting for Alex · 18 hours left”.

**Completed:** Both players have played or the 24 hours have elapsed. Examples include “10 : 8 · Won · +40 XP”, “Draw · 0 XP” and “Lost · −10 XP”, together with the course, deck and opponent.

Win, draw and loss also use symbols, not colour alone. A draw is explicitly labelled Draw, never Loss. When a duel ends through timeout, text such as “Alex did not play · Won” replaces the opponent's score. The opponent's result becomes visible only under Completed. Decline is available only for challenges the user has received.

### New Duel in three steps

1. Choose an opponent: a friend from a searchable friends list, or “Select a random player”. Below the friends list is “+ Add friend”, also available on Profile.
2. Choose a course: three cards for Financial Modeling, Corporate Finance and Investments.
3. Choose a deck mode: Random Deck, labelled Recommended, or Top Decks.

A summary follows, for example “You are challenging Alex · Corporate Finance · Random Deck”, with a Start Duel button. The challenger immediately plays their 15 questions. The duel then moves to Pending for the challenger and Ongoing for the opponent.

Database deck selection:

- Random Deck selects a random deck from all decks in the selected course.
- Top Decks selects a deck from the three highest-rated decks in that course.

Both players receive the same deck and questions in the same order. Only answer order is shuffled separately for each player.

### Gameplay

The game interface resembles Quizduell:

- Header: Course, deck name and opponent, for example “Corporate Finance 1 · vs. Alex”. Do not label it Live, because players take turns.
- Left: A large question above four answers arranged in a 2-by-2 grid.
- Below: A shrinking countdown bar for the 30 seconds allowed per question.
- Right: An overview of all 15 questions, each shown as a green box with a check mark for correct, or a red box with a cross for incorrect or timed out.
- After an answer: The correct answer flashes green. If the chosen answer was wrong, it turns red. The next question then appears automatically.
- Timeout: The question counts as incorrect. Show “Time expired”, not “Not quite right”, and still highlight the correct answer in green.
- Exit: Clicking Exit asks “Really exit? This duel will count as a loss.” Confirming loses the duel.
- Locked navigation: Clicking another tab or Profile during a duel opens the same exit confirmation. Without confirmation, the player stays in the game. Confirming counts as a loss, so navigation cannot bypass the penalty.

### After your round

After question 15, show “Your round is finished” and the user's score, not “Duel completed”, because the final outcome still depends on the opponent.

Below the score, the user must rate the deck using three large buttons: thumbs up, neutral and thumbs down. One click is enough. Rating is mandatory even if the user has rated that deck before, and navigation cannot skip it. Ratings are anonymous and contribute only to the deck's average in the database.

The duel then moves to Pending, or directly to Completed if the user played second.

## Profile page

The profile shows identity, XP, friends and past duels. History opens Review, the main place to learn after playing.

### Profile header

- Name and profile picture.
- Total XP, never below zero.
- Win streak, for example “Win Streak: 3”. After three consecutive wins, show “Next win counts double”.

### Friends

A friends list includes “+ Add friend”, also shown in step 1 of New Duel. This opens a username search; a user is added from the results.

Still to decide: immediate friendship or requests, whether requests can be declined, and how friends are removed. See Open questions.

### History and review

Show the newest duels first. Each entry includes:

- Deck name, opponent and outcome, such as “Won 10 : 8”, Lost or Draw.
- Date, such as “Played on 7 November”, and correct answers, such as “10/15 correct (67%)”.
- A Review button.

Review lists all 15 questions in order, with the user's answer, correct answer, and a check mark or cross. Each question has a Report button for flagging incorrect or faulty content.

Reporting requires confirmation:

1. Report opens “Really report this question?” with Cancel and Report.
2. The report is saved only after Report is confirmed.
3. The button then permanently changes to “✓ Reported”. Each person can report a question only once.

## Calendar reminders

StudyDuel uses the user's Google or Apple calendar to avoid missed deadlines and encourage regular learning.

- **Your 24-hour deadline:** When challenged and due to play, a calendar entry reminds you before the 24 hours expire, helping avoid an accidental loss.
- **Study and quiz reminders:** Regular calendar reminders to play a duel or study a deck.

The calendar connection is configured once, for example in Profile. Reminder frequency and timing are still open questions.

## Decision rules

Only correct answers decide a duel. XP, streaks and time-limit outcomes affect the profile after the duel.

### Duel scoring

A correct answer earns one point. An incorrect answer or 30-second timeout earns zero. There are no negative duel points. Higher scores win; response time is not a criterion. Equal scores are a draw and are labelled accordingly. The same rules apply against friends and random opponents.

### XP after a duel

- Win, first to third consecutive win: +40 XP; streak increases by one.
- Win, fourth consecutive win onward: +80 XP, twice the normal award; streak increases by one.
- Win because the opponent times out: +40 or +80 XP; streak increases by one.
- Draw: 0 XP; streak ends.
- Loss: −10 XP; streak ends.
- Abandonment during play, including confirmed exit through tabs or Profile: −10 XP and a loss; streak ends.
- Not playing within 24 hours: −10 XP and a loss; streak ends.
- Declining a challenge: 0 XP; streak stays unchanged.

XP never falls below zero. The multiplier affects XP only, not points inside the duel.

### Time limits

Each of the 15 questions allows 30 seconds. The opponent has 24 hours to play. Ongoing and Pending cards show remaining time, such as “18 hours left”; the calendar also provides a reminder.

After 24 hours, the player who has played wins automatically. The card explains that the opponent did not play.

### Ratings

A rating is required after every played duel, even for a previously rated deck. Navigation cannot skip it. The three levels are thumbs up, neutral and thumbs down. Individual ratings are anonymous; only the average is visible. Top Decks means the three decks in a course with the best average.

### Reports and administration

An individual question is reported from the Profile review screen after confirmation. Each person can report a question once. At 20 reports, the deck enters the admin view. An administrator decides whether to keep or delete it.

Admin is an account role. Only accounts with that role can see the admin view. Users cannot edit or delete decks after creation; every card remains editable before submission.

## Decision paths

Two workflows underpin the app: a duel's lifecycle and deck creation.

### Duel lifecycle with two decisions and five outcomes

Start New Duel by choosing a friend or random opponent, course and mode. The challenger plays 15 questions and completes the mandatory rating. The challenger waits in Pending while the opponent sees Ongoing.

First decision: Does the opponent respond within 24 hours?

- Declines: Challenge declined, 0 XP and unchanged streak. This is the only ending without a result.
- Does not play within 24 hours: Completed; the challenger wins and the opponent loses 10 XP. The source diagram shows +40 XP for the challenger; the XP rules above also allow +80 for the qualifying streak.
- Plays and rates: Compare scores in the second decision.

Second decision: Is your score higher, equal or lower?

- Higher: Win, +40 XP or +80 from the fourth consecutive win.
- Equal: Draw, 0 XP and streak ends.
- Lower: Loss, −10 XP, streak ends and XP remains at least zero.

Results become visible under Completed. Abandoning during the 15 questions, through Exit or confirmed navigation, counts as a loss.

### Deck creation with three checks and three loops

Choose a course and deck name, then enter cards manually or generate them from lecture material using the future AI option. Every card in the list remains editable and deletable.

1. Is the current card complete? If no, complete it; Add Flashcard remains locked. If yes, continue.
2. Are there already 15 cards? If no, Add Flashcard creates the next card and increases the counter, then returns to the card list. If yes, Save Deck opens a review of all 15 questions.
3. Should this deck be created as shown? If no, return to the card list. If yes, publish the deck. It can no longer be edited or deleted.

Every No returns to the editable card list. Only Yes at the final confirmation makes the deck permanent.

## Page wireframes

The original wireframes illustrate desktop layouts; colours and visual details are left to design. The following English layout descriptions preserve their content and navigation.

### Decks start screen

A header contains StudyDuel, Decks, Play, Leaderboard and Profile. Create New Deck is the primary entry point. Below it are course cards for Financial Modeling, Corporate Finance and Investments. Choosing a course opens its decks and their creators and ratings.

### Deck creation and card list

The creation screen contains course and deck-name fields, a numbered list of 15 cards, the current question, four answers with a single correct-answer selector, Add Flashcard and Save Deck. Completed cards are filled; the current card is outlined. Every card can be selected and edited. Save Deck stays grey until all 15 are complete.

### New Duel step one

The header and breadcrumb lead to Play and New Duel. Select an opponent from the searchable friends list or use Select a random player. Add friend appears below the friends list. Continue moves to course selection and then deck mode.

### Game Overview

A New Duel button appears above Ongoing, Pending and Completed columns. Each card shows course, deck and opponent. Ongoing includes Play and Decline; Pending shows your result and remaining time; Completed shows the final result and XP. The opponent's result appears only under Completed.

### Game interface

The header names the course, deck and opponent. The question and a 2-by-2 answer grid occupy the main area, followed by a 30-second progress bar. A 15-question status grid sits to the right. Exit and navigation require abandonment confirmation. Timeouts explicitly say Time expired.

### Profile friends history and review

The profile header shows picture, name, XP and streak. Friends includes Add friend. Duel history shows dated results and Review buttons. Review opens all 15 questions, the user's answers and solutions. Report first asks “Really report this question?”.

## Historical implementation proposal for reference only

The original plan builds the app in 13 steps, each in a separate Codex session and only after testing the previous step. For the university prototype, the opponent is simulated and all data lives locally in the browser. Real multiplayer with a server and accounts would be a separate, substantially larger project.

Original recommended technology: React with Vite, example data in code and browser localStorage so reloading loses no data. No server and no real login.

1. **Foundation** — Set up the project, Decks/Play/Leaderboard/Profile navigation, page switching, colours and fonts. Effort: low. Risk: low. Priority: Must.
2. **Data model** — Courses, decks, cards, users, friends, duels, ratings, reports and admin role; three courses with two or three example decks each, each containing 15 original questions. Effort: medium. Risk: medium, because everything builds on this. Priority: Must.
3. **View decks** — Course overview, deck list with average ratings, complete questions and solutions, breadcrumbs. Effort: low. Risk: low. Priority: Must.
4. **Create New Deck** — Dropdown, deck name, 15 cards, correct-answer selection, validation, editable/deletable card list and review before submission. Effort: medium. Risk: medium, because of the many validation rules. Priority: Must.
5. **Game interface** — Question, 2-by-2 answers, 30-second bar, green/red feedback, Time expired, status overview, shuffled answers, automatic progression, exit and locked navigation. Effort: high. Risk: high, because of timers and game state. Priority: Must.
6. **Round end and rating** — Your round is finished, mandatory three-option rating, average per deck and top three per course. Effort: low. Risk: low. Priority: Must.
7. **Game Overview and New Duel** — Ongoing/Pending/Completed columns, remaining time, draw and timeout wording; friend or random opponent; Random or Top Decks; decline; 24-hour rule. Effort: high. Risk: high, because opponent and time must be simulated. Priority: Must.
8. **Profile and XP** — XP rules, streak, dated history and percentages, review, report confirmation. Effort: medium. Risk: medium, because of the many edge cases. Priority: Must.
9. **Friends** — Friends list and Add friend search in Profile and New Duel. Effort: medium. Risk: low. Priority: Should.
10. **Admin view** — Decks with at least 20 reports; delete or keep. Effort: low. Risk: low. Priority: Could.
11. **Calendar reminders** — 24-hour deadline plus study/quiz reminders for Google and Apple calendars; downloadable calendar entries may be used in the prototype. Effort: medium. Risk: medium, because a real connection requires provider login. Priority: Could.
12. **AI assistant** — Upload lecture, generate multiple-choice questions with a chatbot, transfer them into the card list for review. Effort: high. Risk: high, because of upload, AI integration and question quality. Priority: Could.
13. **Polish** — Immediate click feedback, calm animations, contrast, symbols rather than colour alone, consistent language. Effort: medium. Risk: low. Priority: Should.

Prototype simulation: The opponent is an example user. Two test buttons demonstrate the scenarios. “Opponent plays now” creates an opponent result producing a win, draw or loss. “Fast-forward 24 hours” demonstrates timeout.

### Original starter prompt for step one

We are building a clickable prototype of the StudyDuel learning app for a university project. Technology: React with Vite, no database, no login; example data in code and game state in localStorage.

Task for this step only: Set up the project and build the foundation.

- StudyDuel at the top left; Decks, Play and Leaderboard in the centre; Profile with an icon at the top right.
- Highlight the active tab. Every tab opens an empty placeholder page.
- Desktop layout, calm and clear styling, generous whitespace and legible type.
- Buttons react immediately when pressed, becoming slightly smaller and changing colour.

At the end, explain in simple terms how to start the app locally.

Working method: After each step, open the app and click through it. Report errors immediately; begin the next step only afterward. The apple-design skill may be added in step 13; it provides little benefit earlier.

## Open questions

- Leaderboard: The page is not yet designed. Profile XP provides its basis.
- Random Deck incentive: Recommended is specified, but the actual reward, such as bonus XP, is undecided.
- Random opponents: Draw from all users or only users in the selected course? What happens if a random opponent declines?
- Add Friends: Immediate friendship or requests? Can requests be declined? How are friends removed?
- Fixed input value: Define exactly what is fixed when adding questions, for example format or character limit.
- Calendar reminders: How often and when? Can reminders be disabled?
- AI assistant: Which file formats can be uploaded, and how many questions are generated per lecture?
- Course enrolment: How is a user's enrolled-course list determined?
- Unrated Top Decks: What appears before a course has rated decks?

## Changes from version one

Version two incorporates feedback on Click Dummy v1:

- Decks: Earlier cards are editable and deletable before submission; questions use a fixed input value; an AI assistant for lecture-based question creation is added as an extension.
- Play: Select a random player; locked navigation during duels; Time expired instead of Not quite right; no Live label; Your round is finished after a player's round; explicit draws; remaining time on Pending cards; explanation when an opponent did not play before timeout.
- Profile: Add friend and confirmation before reporting.
- New: Calendar reminders for 24-hour deadlines and regular study/quiz sessions through Google and Apple calendars.
- Implementation plan: Expanded from 10 to 13 steps, adding friends, calendar and AI assistant.
