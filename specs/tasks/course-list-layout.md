# Course list on Decks

Parent topic: [Appearance and navigation](../appearance-and-navigation.md).

## Why

Students need a quick overview of every course they selected, without switching a course picker before they can choose a learning path.

## What

The Decks page keeps its existing creation area at the top. Beneath it, it presents the student's courses as a vertical desktop-friendly list. Each row shows real counts of available Study and Battle decks plus a direct Study action. Battle decks are the public Battle Mode decks (15-question snapshots) of the student's university and course, read through the read-only `battle_deck_catalog()` function without their questions; retired classic duel decks are not listed. Decks never starts a Battle: all matchmaking starts from **Play → Battle Mode**. If the catalogue cannot be loaded, the page shows a warning and still lists Study decks. Clicking a course row's “Decks in this course (N)” dropdown expands the list of that course's Study and Battle decks inside the row; each deck shows its name, language, author and question count. Study decks offer Open for an owned deck or Save copy for another student's deck; Battle decks are informational here and have no start action. A course without decks says so in the dropdown. The **Browse decks** section is a global catalogue in compact two-column cards, with search by deck name plus course, mode and **Created by me** filters for large catalogues.

## Out of scope

Changing deck visibility, publication, learning progress, Battle matching, or course membership.

## Done when

1. Every course in the signed-in profile appears exactly once as a vertically stacked row.
2. A row displays only counts derived from available decks and opens the existing Study flow; Battle matchmaking remains available only from Play.
3. Browse decks filters show the appropriate existing deck types; Created by me shows only decks owned by the signed-in student, and search plus course filter narrow the global catalogue without persisting data.
4. The original creation controls appear once, above the course list, in light and dark themes.
5. Reloading preserves the profile's courses and deck data; no new course-list data is persisted.
6. Each course row has a deck dropdown that lists exactly that course's available decks, with the same actions as the Browse decks cards.
7. A newly published Battle Mode deck appears in its course row, under the Battle filter and, for its creator, under Mine; other students at the same university with that course see it too, students elsewhere do not.
