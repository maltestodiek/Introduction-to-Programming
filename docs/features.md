# StudyDuel feature index

Current organization as of 13 November 2026. This is the current product map; the [implementation journal](archive/implementation-journal.md) is chronological history.

## Authentication and student profiles — implemented
Email/password signup and confirmation, sign-in/out, recovery, verified session restoration; username, university lookup/manual entry, courses, languages, degree/field, graduation year and photo/avatar. [Specification](../specs/authentication-and-profiles.md).

## Social connections — implemented
Friend codes and invitation links, requests and acceptance, private chat and unread previews. Participant menus work in ongoing/history cards; chat offers friendship controls. [Specification](../specs/social-connections.md).

## Deck authoring and question tools — implemented
Flexible Study decks of up to 100 questions, four-answer questions, subsection/lecture names, mandatory review, revision-safe edits and optional per-question calculator. The separate classic editor retains 15-question immutable decks. Basic text-only Anki import stores private source cards; AI generation remains a placeholder. [Specification](../specs/deck-authoring.md).

## Study Mode and learning progress — implemented
Solo/together settings, chapter/level preferences, friend/random/open-session matching, shared question sets, 24-hour deadlines, feedback and notes, progress colours, results without XP and immutable earned copies. [Specification](../specs/study-mode.md).

## Battle Mode — planned redesign; classic engine retained
The new Battle Mode entry is Coming soon. The previous 30-question engine and saved rounds/reviews remain. The team's Battle Pool proposal is preserved for review and is not the current Study specification. [Specification](../specs/battle-mode.md).

## Appearance and navigation — implemented
One topic for logo/branding, welcome design, dark/light/system themes, backgrounds, icons, hover effects, responsive layouts, menu cards, progress legend, ongoing/history sections and chat/calculator layout. [Specification](../specs/appearance-and-navigation.md).

## Future work
Leaderboard, Study Plan, shared university course discovery and AI slide import need their own reviewed task specs before implementation. Historical proposals do not authorize them automatically.

## Definition of done
Use the lecture's Why / What / Out of scope / Done when task format. For stateful workflows, identify state, durable storage, allowed/rejected actions and a full process restart check. Current verification evidence and limitations are in [implementation status](implementation-status.md).
