# PDF lecture-slide import

## Why

Students should be able to turn their private lecture slides into reviewable StudyDuel questions through the same protected source-to-draft workflow used for Anki cards.

## What

An authenticated student can upload one text-based `.pdf` lecture file from Decks. StudyDuel extracts selectable text page by page, keeps at most 100 bounded private sources, and saves them in the existing private-source schema. The student can then select those sources, generate private AI drafts, review them, and explicitly create a Study deck.

## Out of scope

PowerPoint, Keynote, Word, images, OCR, encrypted PDFs, public raw-slide sharing, and automatic deck publication.

## Done when

1. A signed-in owner can upload a readable PDF below 20 MB and save up to 100 private text sources.
2. A scanned, encrypted, malformed, empty, or oversized PDF is rejected without creating an import.
3. PDF sources use the existing selection, AI generation, review, and Study-deck flow without exposing the uploaded PDF or provider credentials.
4. Another user cannot read or generate from the owner's PDF sources, and imports survive a restart.
