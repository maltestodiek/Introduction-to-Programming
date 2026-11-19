# Deck studio

Parent topic: [Deck authoring](../deck-authoring.md).

## Why

Students lose track of the decks they created: new AI-generated Study decks are private and do not appear in the course overview, and the app showed no time when a deck was created, edited or published.

## What

A large **Deck studio** card on the Decks page, between the deck creation cards and Your courses, shows a short description and an **Open Deck studio** button that opens a page that lists only the signed-in student's own Study and Battle decks, newest first. Filters show All, Private, Published and Battle decks with their counts.

Each Study deck shows its course, language, question count, status (Private, only visible to its creator, or Published since a time), its creation time and its last edit. Actions are Edit (opens the existing Study editor with the deck), Publish or Unpublish, and Battle, which opens Create Battle Mode Deck with this deck already selected and returns to Deck studio. Battle needs at least 15 questions. Each Battle deck shows its creation time, is marked as a public fixed snapshot and offers Start Battle.

Times are shown in the viewer's browser time zone (Europe/Berlin when it is unknown), for example "19 Nov 2026, 20:25".

`supabase/deck-studio.sql` adds `study_decks.created_at`, filled automatically for new decks, and the read-only `deck_studio()` function. Study decks had no creation time before: existing decks get the time of their first review, which always precedes the first save; decks without a review, such as copies, keep an unknown creation time and show "Created on or before" the date of their last edit instead of an invented time. The function returns metadata only, never questions, and only the caller's decks.

## Out of scope

Deleting decks, editing Battle snapshots, showing other students' decks, changing publication or Battle rules, and recording the origin (manual, Anki, slides) of Study decks.

## Done when

1. Deck studio lists exactly the signed-in student's own Study and Battle decks; another student's decks never appear.
2. Private, Published and Battle filters show the matching decks; Publish and Unpublish change the status through the existing publication action.
3. Every deck shows its creation time in the viewer's time zone, or an honest "on or before" date when it was not recorded; Study decks also show their last edit and publication time.
4. Edit opens the Study editor with the deck; Battle opens the Battle creator with the deck selected and Back returns to Deck studio.
5. `tests/deck_studio_database.mjs` passes in isolated PGlite, and the creation times survive a full restart because they are stored in PostgreSQL.
