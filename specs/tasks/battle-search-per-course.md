# Battle searches per course

## Why
Students who finished a random Battle must be able to play another course while waiting for an opponent.

## What
- Persist one search per user and normalized course (trimmed, case insensitive), across languages.
- Different courses may wait simultaneously. A second random search for the same normalized course is rejected, regardless of language or selected deck; the student manages that search through Active battles.
- Matching and cancellation remove only the affected course's search. Every unmatched session retains its own round and search deadlines and overview card.
- Preserve legacy single-search responses while returning a `searches` array. Unscoped legacy cancellation must reject when multiple searches exist.

## Out of scope
Changes to university/course/language eligibility, friend invitations, answer validation, XP, forfeits, the one-hour round limit or the 48-hour matching window.

## Done when
- Two courses can wait across a database restart, without losing their sessions.
- Duplicate course searches, including case/space variants and other languages, are rejected with a clear message and do not reopen the saved round or its rating screen.
- Matching, cancelling or expiring one course leaves the other untouched.
- Other users cannot cancel someone else's search; started unfinished rounds still require the existing forfeit flow.
- Existing Battle regression checks pass using only isolated fixtures.

## Verification and release
Run `tests/battle_database.mjs` with PGlite and the Battle Python tests. Apply `supabase/migrations/20261123090000_battle_search_per_course.sql`, then `supabase/migrations/20261123100000_reject_duplicate_course_battle_search.sql`, after the async and leave-loss migrations. No existing search rows are deleted by the migrations. The current UI already renders one card per unmatched session; verify two cards manually in a test environment, each with its own cancellation action. The migration also supports the previous UI's session-based cancellation.
