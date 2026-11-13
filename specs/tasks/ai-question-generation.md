# AI question generation from imported sources

## Why

Students need a safe, reviewable way to turn private study material into multiple-choice drafts without exposing provider credentials or allowing unreviewed AI output in Study Mode.

## What

An authenticated student can select up to 100 eligible source cards from one private import and request one multiple-choice draft per selected card. The first implementation uses Basic Anki source cards. Lecture-slide sources may use the same generation and review workflow only after their own extraction and source-review task is approved.

The frontend sends only an import ID and selected source-card IDs to a Supabase Edge Function named `generate-questions`. The function:

1. verifies the signed-in user;
2. loads source cards and access rights only from Supabase;
3. sends only the selected front/back text to Requesty;
4. requires JSON-only output;
5. validates every proposed question before any write;
6. saves valid output as private `draft` questions;
7. returns a clear error without changing source cards if a provider, timeout, parsing or validation error occurs.

Each AI draft contains a question, exactly four answer options, exactly one correct option index from 0 to 3, an explanation and its `sourceCardId`. Options must be non-empty and unique after normalisation. The source card must belong to the request.

The Requesty key is stored exclusively as the Supabase secret `REQUESTY_API_KEY`. It is never returned to the browser, committed to Git or placed in Streamlit secrets.

A student reviews every draft, can edit or discard it, and explicitly publishes the approved questions into a StudyDuel deck. A published deck may contain one to 100 questions. Drafts never appear in Study Mode or in playable deck lists.

### Limits and concurrency

The UI can select up to 100 source cards for one deck-generation request. The Edge Function processes those cards in internal batches of at most 10 to stay within provider and function time limits. It creates no partial saved result: if any batch fails or any response is invalid, no generated question from that request is saved.

Only one generation request per signed-in user may run at a time. A second request receives a clear “generation already running” response and changes no data.

### State and persistence

| State | Durable data | Allowed action | Rejected action |
| --- | --- | --- | --- |
| Imported source | private Anki import and source cards | select up to 100 cards | select another user's cards |
| Generating | per-user generation lock | wait for result | start a parallel request |
| AI draft | private draft questions with provenance | edit, discard or publish | play or share directly |
| Published | validated StudyDuel deck/questions | use in Study Mode | silently overwrite after publication |

Source cards remain unchanged throughout generation, review, publishing, provider errors and browser restarts. Drafts and their source provenance also survive a full restart.

## Out of scope

Lecture/PDF text extraction, image/OCR processing, Cloze/media conversion, chatbot functionality, automatic publication, provider fallback, and sending raw files or API keys to the browser.

## Done when

1. A signed-in owner can select one to 100 Basic Anki source cards and receive one valid private MC draft per card.
2. The browser never receives `REQUESTY_API_KEY`, raw provider credentials or a service-role key.
3. Invalid JSON, malformed options, provider errors and timeouts save no draft questions and preserve the raw source cards.
4. A second simultaneous request from the same user is rejected without changing existing data.
5. A student can edit, discard or explicitly publish drafts; only published questions are playable.
6. Another user cannot read, generate from, edit or publish the owner's source cards or drafts.
7. Tests use simulated Requesty responses only and cover valid output, malformed JSON, invalid options, wrong source IDs, provider failure, concurrency and the 100-card limit.
8. The full source → draft → reviewed deck workflow survives an application restart.
