# Study Mode and learning progress

## Why
Practise alone, or discover another student's course material asynchronously, without XP or rankings.

## What
Study decks support one or more four-option, one-solution questions and optional chapters. Existing published 15-card decks remain intact and can be studied by their owners. A Study copy can be created for editing; new Study decks are private until explicitly shared through a session. Review is mandatory before saving content. Optimistic revision checks prevent overwriting concurrent edits.

Per-user progress is New (unanswered), Needs practice (answered level 0), orange level 1, yellow level 2, green level 3. Correct raises one, wrong lowers one, bounded 0–3. Question content changes create a new progress identity; chapter-only changes do not. Answers from existing duels also update progress exactly once. Private notes and feedback reference the immutable question content version. Feedback is explicitly sent to its author and remains visible to the sender. Private notes are never sent.

Solo selects an owned or earned deck, chapters, any combination of levels, and 1–100 or all eligible questions. No repeats within a session, no timer, saved answers, immediate feedback, explicit Next question, resumable after navigation/restart.

Together selects an owned deck, course, language and 20/40/60/80/100 questions. Each contributes half without replacement. The complete deck is snapshotted when starting. Own questions are answered first, partner questions second. Random pairing requires mutual opt-in, same university/course/language/size, compatible profile languages, and different decks. Ready searches last 24 hours. Only one outstanding random search per user. Open sessions can be joined explicitly, reserving the partner immediately and beginning a 24-hour completion deadline. Friend invitations require an accepted friendship, recipient acceptance and compatible decks; both friends must have the course in their profiles. There is no course-mismatch override. Invitations are visible only after the sender completes their own half. No external messages are sent.

After matching, each player has 24 hours to finish. A completed player immediately earns a permanent full copy of the partner's snapshot even if the partner does not finish. An unfinished player receives no full copy. Future original edits do not propagate. Both finished: compare correct-answer counts, show win/draw/loss; no XP, streak or rating changes. Otherwise show pending or partner did not finish. Unmatched expiry/cancellation preserves practice. No automatic matching with idle non-consenting people.

## Out of scope
New competitive Battle rules, AI/Anki import, chat, email/push notifications, live gameplay, automatic chapter-name quality checking. Chapter labels must not reveal answers (author guidance).

## Done when
Tests verify variable deck sizes and review, optimistic edit rejection, correct progress transitions and content identity, chapter/level intersection, no duplicate questions, exact half sizes, immediate locked feedback and explicit Next, restart persistence, mutual random eligibility, reservations, friend acceptance/decline, deadline enforcement, earned immutable copies, private notes and author feedback, score visibility and zero XP/streak changes. Unauthorized/rejected writes leave data unchanged. Run existing regression checks as well.

## Together sampling refinement — 13 November 2026
Learning levels are preferences for selecting the contributor's own half, not matching constraints. Prefer all available questions in the chosen levels, then fill a shortage randomly from other questions in that same deck without replacement. Both students still receive the identical combined question set. No chapter filter is offered in Together. A 40-question session requires 20 questions from each deck even if fewer than 20 match the preferred levels. The UI explains both the split and any fallback.


Creation update: the main Create New Deck button opens the flexible deck editor. Authors can type new subsection/lecture names or reuse existing ones; the next question inherits the current subsection. No fixed deck question limit. Classic 30-question duels retain a separately labelled 15-question editor. Display coloured markers alongside learning-level names in both session settings dropdowns.

## Related feature ownership
Deck creation, subsection authoring and calculator permissions belong to [Deck Authoring](deck-authoring.md). Session cards, mode selection and the shared colour legend presentation belong to [Appearance and Navigation](appearance-and-navigation.md). Friend requests and messages belong to [Social Connections](social-connections.md). This specification owns sampling, matching, answer feedback, learning levels, notes, copies and Study results.
