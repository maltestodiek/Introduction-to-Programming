# Text from images on Anki cards

Parent topic: [Deck authoring](../deck-authoring.md). Extends [Basic Anki text-card import](basic-anki-import.md).

## Why

Many Anki decks put the content on images: screenshots of slides, formulas or tables. These cards were skipped, so students lost much of their deck when generating questions.

## What

Two-field Basic notes with images are no longer skipped. The importer reads the package's media (the JSON map of older exports and the zstd-compressed protobuf map of current exports) and keeps cards whose images are PNG, JPEG, GIF or WebP, at most 4 MB each and at most three per card. Such cards count towards the 100-card limit.

After checking the package, the import screen shows how many cards contain images and a **Read text from N image cards** button. For each card, the images are sent to the new Edge Function `extract-image-text`, which verifies the signed-in user, validates the images and asks a vision model through Requesty (`REQUESTY_VISION_MODEL`, default `openai/gpt-4o-mini`) to transcribe the readable text exactly, without describing pictures. The text read from each image is added to the written text of its side. The images are not stored and are not interpreted as pictures; only the text is used.

The student reviews and corrects the text of every image card before saving. Cards with an empty side are not imported. Saved image cards become ordinary private text source cards, so question generation, review and publication work unchanged. The Requesty key stays a Supabase secret.

Audio and video cards are still skipped (`media`). Image cards whose image is missing, of another type, too large or one of more than three are skipped (`image`).

## Out of scope

Storing images, describing diagrams without text, Cloze, audio or video cards, and a per-user quota for image reading.

## Done when

1. Image cards from older and current Anki exports are recognised with their images; text cards import as before.
2. The text read from the images appears in an editable review, and only reviewed cards with text on both sides are saved as source cards.
3. A failed or empty reading shows a clear message and saves nothing for that card; the rest of the import still works.
4. The Edge Function rejects unsigned requests, more than three images, other image types and images over 4 MB, and never logs image data or text.
5. Tests: `tests/test_anki_import.py`, `tests/test_anki_image_text.py` and `supabase/functions/extract-image-text/vision_test.ts` use simulated Requesty answers only.
