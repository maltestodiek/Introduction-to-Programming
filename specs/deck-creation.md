# First feature Create and reopen a reviewed deck

## Why

A student needs a trustworthy course deck before they can study or duel. Let them compose, inspect, correct, and permanently confirm exactly 15 complete questions, then reopen those same questions and solutions after restarting the app.

## What

Use the existing class scaffold and a clearly labeled fictional demo creator. Offer the three specified courses. Keep an unconfirmed draft in session memory: course, name, ordered cards, question text, four ordered answers per card, and exactly one selected correct answer.

Create New Deck begins with one empty card. Add Flashcard requires the current card to be complete and is unavailable at 15 cards. Show Card N of 15. Any earlier card can be edited or deleted. Deletion preserves the relative order and correct-answer associations of surviving cards. A deleted slot can be replaced by adding another card; a draft may contain fewer than 15.

Proposed input rules for group review: trim outer whitespace; require nonblank deck name, question, and all answers; require a listed course; allow repeated deck names and repeated question/answer text because the source does not prohibit them. No invented length limits or arbitrary 'fixed input' constraint. Reject absent, multiple, or out-of-range correct-answer selections at the rules layer, even though the UI uses a single-choice control.

Save Deck opens review only for exactly 15 valid cards and valid deck metadata. Review lists all 15 questions, all four answers, and exactly one marked solution per question. It creates no permanent deck. Back to editing preserves all content and invalidates the prior review. After any edit, the revised draft must be reviewed again.

Create Deck is available only from a valid current review. Validate again before writing. In one transaction, save the deck, its creator and course, its 15 ordered cards, and answer identities/correct-answer associations. A failed validation or storage write must create no partial deck. Repeating the confirmation for the same draft must not create a duplicate deck; a new draft may use the same name.

After success, display a read-only deck. Add it to its course's deck list with creator. Ratings are not implemented in this slice: show Not rated rather than a fabricated average. Users have no edit/delete actions for confirmed decks. Reopen the same saved content after a full Streamlit process restart using the same SQLite file.

## Out of scope

Real signup, enrollment, multiplayer, timers, answer shuffling during play, duels, ratings, XP, leaderboard, reports, moderation, friends, calendar integrations, AI uploads, design polish, and deployment. No requirement to recover unconfirmed drafts after a process restart. No preview app or placeholder game implementation is part of this planning task.

## Done when

1. With an empty temporary database and demo creator, choose Corporate Finance, name a deck Corporate Finance 1, and enter 15 complete original cards. Each has four answers and one correct choice. Save Deck opens the full review; the database still contains zero decks. Create Deck saves exactly one deck with 15 cards and 60 answers.
2. Start an incomplete card, leave Answer 4 blank, and try Add Flashcard. An actionable error appears, and no card is added. At 14 complete cards, Save Deck cannot proceed. At 15, a sixteenth card cannot be added.
3. Edit card 3 and its correct choice, delete card 7, and add a replacement. Review shows the changed content and current order. Go back, edit again, and confirm only after reviewing the revised version.
4. Attempt confirmation with an invalid 14-card draft or a blank answer through the business-rule entry point. It fails; no partial deck appears and any existing saved deck is unchanged. Repeating a successful confirmation for its draft leaves the saved count at one.
5. Stop Streamlit, start it again against the same database, browse Decks > Corporate Finance > Corporate Finance 1, and compare all questions, answer orders, solutions, name, course, and creator. They match the confirmed review. There are no edit/delete controls for the saved deck.

Acceptance details beyond the source (whitespace handling, repeated names, confirmation retry behavior, and draft durability boundary) are proposals to review before coding.
