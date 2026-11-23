# Deck studio

Parent topic: [Deck authoring](../deck-authoring.md).

## Why

Students lose track of the decks they created: new AI-generated Study decks are private and do not appear in the course overview, and the app showed no time when a deck was created, edited or published.

## What

The studio heading carries the design-services icon used on its entry button, and the Study deck view (shown after creating or publishing a deck) offers a highlighted **Open Deck studio** button beside Back to Study decks.

A large **Deck studio** card on the Decks page, between the deck creation cards and Your courses, shows a short description and an **Open Deck studio** button that opens a page that lists the signed-in student’s own decks and earned Study Together copies, newest first. Filters show All, Private, Published, Battle and Study Together decks without counts.

Each Study deck shows its course, language, question count, status (Private, only visible to its creator, or Published since a time), its creation time and its last edit. Actions are Edit (opens the existing Study editor with the deck), Publish or Unpublish, and Battle, which opens Create Battle Mode Deck with this deck already selected and returns to Deck studio. Battle needs at least 15 questions. Each Battle deck shows its creation time and is marked as a public fixed snapshot; new Battles start only from Play.

In **Decks → Your courses**, published Study decks offer **Study** and **Add to my Deck Studio**. Adding keeps the course list open. It creates or reuses a private editable copy, or restores a previously removed listing. A visible copy shows **In my Deck Studio**. Apply `supabase/migrations/20261123040000_add_published_deck_to_studio.sql` after the personal removal migration.

Finishing both halves of Study Together adds the partner’s full snapshot to **All** and **Study Together**, including copies earned before the Studio update. The row shows the recorded author and receipt time. **Open deck** opens its read-only questions and personal progress. Other Studio rows credit the creator or, for a saved course deck, its source publisher. Apply `supabase/migrations/20261123100000_earned_decks_in_studio.sql` after the published-course-deck migration.

Study deck owners can choose **Remove from my studio** and confirm or cancel. Confirmation hides that listing in all of their Studio filters, including on other devices. Publication, shared copies, existing sessions and Battle snapshots keep their existing access. The owner’s other Study screens can still open the deck. Apply `supabase/migrations/20261123030000_personal_deck_studio_removal.sql` after the original Deck Studio schema.

Times are shown in the viewer's browser time zone (Europe/Berlin when it is unknown), for example "19 Nov 2026, 20:25".

`supabase/deck-studio.sql` adds `study_decks.created_at`, filled automatically for new decks, and the read-only `deck_studio()` function. Study decks had no creation time before: existing decks get the time of their first review, which always precedes the first save; decks without a review, such as copies, keep an unknown creation time and show "Created on or before" the date of their last edit instead of an invented time. The function returns metadata only, never questions, and only the caller's decks.

## Out of scope

Permanently deleting deck content, editing Battle snapshots, showing other students' decks, changing publication or Battle rules, and recording the origin (manual, Anki, slides) of Study decks.

## Done when

1. Deck studio lists the signed-in student's visible personal decks and their earned Study Together snapshots. Another student’s private listings stay hidden.
2. Private, Published and Battle filters show the matching decks; Publish and Unpublish change the status through the existing publication action.
3. Every deck shows its creation time in the viewer's time zone, or an honest "on or before" date when it was not recorded; Study decks also show their last edit and publication time.
4. Edit opens the Study editor with the deck; Battle opens the Battle creator with the deck selected and Back returns to Deck studio.
5. `tests/deck_studio_database.mjs` passes in isolated PGlite, and the creation times survive a full restart because they are stored in PostgreSQL.
