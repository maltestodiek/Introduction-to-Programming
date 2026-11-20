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
7. retries one malformed or temporary provider response for the affected batch and, when otherwise valid questions omit sources, requests only the missing sources before returning a clear diagnostic without changing source cards if recovery fails.

Each AI draft contains a question, exactly four answer options, exactly one correct option index from 0 to 3, an explanation and its `sourceCardId`. Options must be non-empty and unique after normalisation. The source card must belong to the request.

The Requesty key is stored exclusively as the Supabase secret `REQUESTY_API_KEY`. It is never returned to the browser, committed to Git or placed in Streamlit secrets.

A student reviews every draft, can edit or discard it, and explicitly publishes the approved questions into a UniArena deck in one step from that review: the app performs the Study review handshake (`review_deck` then `save_deck` with the identical reviewed snapshot) and marks the drafts published, without routing through the Study deck editor. The created deck remains editable later under Decks like any other Study deck. A published deck may contain one to 100 questions. Drafts never appear in Study Mode or in playable deck lists.

### Limits and concurrency

The UI can select up to 100 source cards for one deck-generation request. The Edge Function processes those cards in internal batches of at most 10 to stay within provider and function time limits. It creates no partial saved result: if any batch fails or any response is invalid, no generated question from that request is saved.

Only one generation request per signed-in user may run at a time. A second request receives a clear “generation already running” response and changes no data.

### Answer quality safeguards

Language models put the correct answer first far more often than chance and tend to make it the longest, most detailed option. Production drafts showed 86% of correct answers at position A and the correct option as the longest in 64% of questions. UniArena therefore does not trust the model's answer order or answer lengths:

- After validation, the Edge Function moves every correct answer to a server-chosen position. Positions are spread evenly over A–D across the whole request, starting at a random position, and the distractors are shuffled into the remaining slots. The answer texts themselves are not changed.
- The prompt asks for four options of similar length, detail and grammatical form.
- A question gives its answer away by length when the correct option is the longest, at least 1.5 times the average distractor length and at least 12 characters longer than the longest distractor. Such questions are requested once more with a rewrite instruction. A rewrite replaces the original draft only when it no longer gives the answer away; if it fails, the original valid draft is kept because the student reviews every draft.
- Requesty is asked for strict structured JSON (`json_schema`). If the routed model rejects structured output with HTTP 400, the same request is sent once in JSON mode. The validator applies the same rules to both.
- An empty or incomplete batch is retried once and then completed with a request for only the missing source cards.

Batches run with at most five in parallel so that a 100-card request stays within the Edge Function time limit. After a failed batch no new batch starts, and the generation lock is released only after all running batches have finished. The function logs only batch size, model, response format, duration and token counts, never source or question text.

The generate button disappears while a request runs; the request is removed from the Streamlit session before the provider call, so a rerun or double click cannot send it twice. In its place an estimated progress bar shows the remaining time. The app receives no progress from the single Edge Function call, so the estimate assumes about 35 seconds per round of up to five parallel 10-card batches plus 10 seconds start-up (45 seconds for up to 50 cards, 80 seconds for 51–100). The bar reaches 90% at the estimate, then creeps towards 95% with the text “Almost done” and never shows completion before the result arrives. If the Edge Function batch size or parallelism changes, the constants in `logic.py` must change with it.

### State and persistence

| State | Durable data | Allowed action | Rejected action |
| --- | --- | --- | --- |
| Imported source | private Anki import and source cards | select up to 100 cards | select another user's cards |
| Generating | per-user generation lock | wait for result | start a parallel request |
| AI draft | private draft questions with provenance | edit, discard or publish | play or share directly |
| Published | validated UniArena deck/questions | use in Study Mode | silently overwrite after publication |

Source cards remain unchanged throughout generation, review, publishing, provider errors and browser restarts. Drafts and their source provenance also survive a full restart.

## Out of scope

Lecture/PDF text extraction, image/OCR processing, Cloze/media conversion, chatbot functionality, automatic publication, fallback to another AI provider, and sending raw files or API keys to the browser.

## Done when

1. A signed-in owner can select one to 100 Basic Anki source cards and receive one valid private MC draft per card.
2. The browser never receives `REQUESTY_API_KEY`, raw provider credentials or a service-role key.
3. Invalid JSON, malformed options, provider errors and timeouts save no draft questions and preserve the raw source cards. The user-facing error identifies the failed batch size and the precise validation failure after a retry is exhausted.
4. A second simultaneous request from the same user is rejected without changing existing data.
5. A student can edit, discard or explicitly publish drafts; only published questions are playable.
6. Another user cannot read, generate from, edit or publish the owner's source cards or drafts.
7. Tests use simulated Requesty responses only and cover valid output, malformed JSON, invalid options, wrong source IDs, provider failure, concurrency and the 100-card limit.
8. The full source → draft → reviewed deck workflow survives an application restart.
9. Correct answers of generated drafts are spread evenly over the four positions, independent of the model's own order, and no answer text changes when positions move.
10. A draft whose correct option gives the answer away by length is rewritten once; the original is kept when the rewrite fails or is no better.
11. A 100-card request processes batches in parallel (at most five at once) and a single click or rerun starts exactly one generation.
12. While drafts are generated, an estimated progress bar with the remaining time replaces the generate button; it never reaches 100% before the result arrives.
