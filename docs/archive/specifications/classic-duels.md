# Fourth feature Play

## Why
Students need real, consent-based challenges without unsolicited random matches or invitation spam.

## What
Use Python, Streamlit and Supabase. The user approved 30 questions (all 15 from each selected deck), friend invitations, mutual random-search opt-in, and matching deck language with player languages. This replaces the old single-deck/15-question duel flow.

Choose course and a published deck with a declared language. Both players must list that language; both selected decks must have the same course and language. Random matches also require the same university, selected course, activity within 24 hours, and active explicit searches. One queue entry per user; search expires one hour after the player explicitly joins or renews it, with cancellation available at any time. Refreshing the page or automatic polling does not extend the search. A match atomically consumes both entries. There is no background invitation of unqueued people.

Friends can be invited even without the course, but only after an explicit warning confirmation. No course is silently added. Language mismatch blocks the invitation. The recipient chooses a deck and accepts; until then neither round starts. Eligible decks include their university's same-course/language decks and the invited deck. If both choose the same deck, its 15 questions appear twice; disclose this before acceptance.

One pending invitation/active duel per pair, up to five outgoing and ten incoming pending invites, at most five newly sent invites per hour, 24-hour decline cooldown, recipient pause control, and 24-hour invitation expiry. Decline/cancel/expiry gives no XP.

On acceptance/matching snapshot both decks in a fixed shared order. Each player gets independently shuffled answer options. The server owns the question index, 30-second deadline, answers, scoring and 24-hour round deadline. Refreshing does not reset a started question. Repeated/stale answers cannot score twice. Reveal solutions after answering; hide the opponent's score until completion. Ratings for both distinct decks are required to finish the round. Same-deck selection needs one rating. All content was already intentionally studyable through Decks.

Outcomes: higher completed score wins; tie draws. If one completes and the other misses the deadline, the completer wins. If neither completes, both lose with no winner. Confirmed abandonment is a loss and awards the opponent a win. Apply original XP/streak rules once (40/80 win, 0 draw, -10 loss, floor zero). Navigation during a started round requires abandonment confirmation; cancelling stays in play. Before starting a round, leaving Play is safe. Closing a browser leaves server progress and timers running; it does not reset the round.

Old decks have no inferred language. Their creator can set the missing language once; quiz content remains immutable. New deck creation requires language from the creator's profile. Anonymous users and third parties cannot read private matches, queues, answers, presence or ratings. Only aggregate ratings may be exposed later.

## Out of scope
Realtime chat, calendar integration, leaderboard UI, AI/Anki, admin reports and a persistent draft editor. Course identity currently uses normalized course names and university names; aliases are not automatically unified.

## Done when
Isolated database checks prove consent, course/language/university/activity eligibility, cancellation/expiry, invitation caps and cooldown, authorization, exact shared 30-question snapshot, server timers, immutable answer retries, hidden opponent scores, idempotent XP and saved progress across a fresh process. Python UI checks cover choices, warnings, playing, completion and navigation guards. No synthetic records are written to production.
