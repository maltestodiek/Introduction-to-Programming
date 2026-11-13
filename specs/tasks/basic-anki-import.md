# Basic Anki text-card import

## Why

Students should be able to preserve the text content of an Anki deck in StudyDuel before converting selected cards into reviewed multiple-choice questions in a later AI feature.

## What

An authenticated student can upload one `.apkg` file from Decks. The importer accepts only two-field Basic text notes, stores at most 100 source cards in a private Supabase import, and reports skipped notes. Cloze notes and notes containing images/media are not stored and receive specific errors. Imported source cards are not playable questions and never appear in Study Mode until a later reviewed publication flow creates questions from them.

## Out of scope

AI generation, Cloze conversion, media extraction, shared imports, quiz publication, and deleting source imports.

## Done when

1. A signed-in user imports one Basic `.apkg` with text-only notes and receives a private import with the same front/back text and order.
2. Cloze and image/media notes are skipped with distinct messages; valid Basic notes in the same file remain importable.
3. Only the first 100 valid notes are stored. Invalid archives create no import or cards.
4. Another user cannot read or create cards in the first user's import. Imported cards survive a full restart.
