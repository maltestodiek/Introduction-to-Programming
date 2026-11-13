# First feature verification proposal

This is a proposed test plan, not executable tests and not a test result. Review the expected outcomes before implementation.

## State and persistence

Temporary state: the selected course, deck name, draft identifier, ordered draft cards, selected correct answers, current editor view, and the exact draft revision approved for review.

Persistent state: demo creator identity, course identifiers and names, confirmed deck identity and draft confirmation token, ordered cards, ordered answer identities/text, and each card's correct answer identity. Persist the entire deck atomically. A rejected action leaves saved data unchanged. Deck content is separate from future player progress.

A restart test must open the same SQLite file from a fresh process/connection. Each automated persistence test gets its own temporary database. Unconfirmed drafts are intentionally not restart-persistent in this first slice.

## Proposed files

- app.py: authoring, cards list, review, confirmation, course browsing, and read-only deck screen.
- logic.py: pure input validation, card addition/deletion rules, exact-15 deck validation, and review revision rules.
- db.py: schema initialization, demo identity/courses, atomic confirmation, duplicate-confirmation protection, and read-only queries.
- tests/conftest.py: temporary database and 15 original question fixtures.
- tests/test_deck_rules.py: draft validation and transitions.
- tests/test_deck_storage.py: atomicity, confirmation retries, and reload.
- tests/test_deck_ui.py: Streamlit AppTest interactions where supported; manual checks cover the full visual workflow.
- pyproject.toml and uv.lock: add dependencies during implementation.
- docs/product-brief.md and specs/authentication-and-profiles.md: reviewed source of expected outcomes.

Do not create application code, dependencies, or tests until the planning review is complete.

## Tests to write first

### Allowed workflow
Create a complete 15-card draft for Corporate Finance. Use a fixture whose correct choice cycles through all four answer positions so position errors are detectable. Open review: no permanent deck exists. Confirm: expect one deck, exactly 15 cards and four answers each, and an exact match of all content, order, metadata, and correct choices.

### Invalid actions
Check incomplete question, whitespace-only answer, missing answer, three or five answers, no correct answer, multiple correct answers, out-of-range selection, blank deck name, and unsupported course. A saved deck requires exactly 15 cards: reject 0, 14, and 16 at the business boundary. An incomplete current card blocks Add Flashcard. At 15 cards, adding another is rejected. Check the draft as well as database contents remain unchanged on rejection.

### Editing and review
Edit an earlier card's text and solution. Delete a middle card and compare all survivors and their solution identities. Add a replacement. Verify Back to editing retains every field. Modify a reviewed draft and attempt direct confirmation: require a fresh review. Ensure the newly displayed review matches what is persisted.

### Persistence and retry
Save a valid deck, reject a second invalid draft, and compare the first deck field by field. Confirm the same draft twice and expect one record; confirm a separate valid draft with the same name and expect two records under the proposed naming rule. Inject a storage failure after writing deck metadata but before all cards are written: expect full rollback, not an incomplete deck.

Close the database connection, reopen the same temporary file, and compare all saved values. Also run the manual full-process restart check below.

### Read-only behavior
Verify confirmed decks have no editing/deletion controls or user update/delete operations. Opening a saved deck must not change it. All solutions are visible as intended. Do not implement admin deletion in this feature.

## Manual walkthrough after implementation

1. Run uv sync, uv run pytest -q, then uv run streamlit run app.py.
2. Try Add Flashcard on an incomplete card. Check the error and unchanged count.
3. Complete 15 cards, edit an earlier card, delete a middle one, and replace it.
4. Open review, go back and amend a solution, then review again.
5. Confirm and browse the stored deck. Verify every question and answer.
6. Stop the Streamlit process, restart the same command, and reopen the deck. Browser refresh alone is insufficient.
7. Report actual test output and changed files, review the diff, then follow the class commit/branch/review workflow. No push or merge is part of preparing this plan.

## Decisions before implementation

- 'Fixed input value' in the source is undefined. Confirm whether it means a format or a length limit; do not invent one.
- Review the proposed trimming, duplicate-name allowance, and unsaved draft restart boundary.
- Approve this complete deck workflow as the first feature. It changes the source's 13-step sequence without changing the deck rules.
- Confirm repository visibility before publishing: the class instructions request private; this repository was previously observed as public.

## Questions for later features

Define leaderboard ranking and ties; random-opponent eligibility; friend request/removal behavior; enrollment; rating averages and ranking ties; selection among the top three and the unrated fallback; the exact start of the 24-hour timer and whether finishing answers or rating meets it; outcomes for abandonment before opponent play and browser closure; ordering simultaneous duel completions for streaks; report threshold aggregation; consequences of admin deletion; calendar settings; and AI upload formats/count. These do not block deck authoring.
