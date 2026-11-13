# StudyDuel — current product brief

StudyDuel helps students create reviewed course questions, practise independently or with classmates, track learning progress and communicate privately. The interface, documentation and tests are in English.

## Approved implementation
Python and Streamlit, run with uv, with pytest for Python checks. Supabase Auth handles accounts; PostgreSQL and private Storage hold shared durable data. This is the group's approved extension of the lecture's SQLite starting point. No React frontend or new chat/calculator provider is used.

## Product responsibilities
The [feature index](features.md) and [named specifications](../specs/README.md) define the current behavior. Authentication and Profiles owns identity and profile privacy. Social Connections owns friendships and messages. Deck Authoring owns content/review/subsections/calculator permissions. Study Mode owns learning and asynchronous study rules. Appearance and Navigation owns themes, branding and screen organization. The redesigned Battle Mode remains planned; classic saved duels are retained.

Study decks have flexible question counts with four answer choices and one correct answer per question. Solo Study supports chapter/level selection; Together uses 20/40/60/80/100 questions, half from each deck, with the same questions for both participants. Matching requires explicit participation. Completed participants earn immutable copies of the other deck; author edits do not propagate. Study results do not award XP. See the Study spec for deadlines, matching details and feedback privacy.

Saved content, progress, friendships and messages must survive restarts and deployments. Authorization is enforced in Supabase, not just by hiding UI. Invalid actions leave saved state unchanged. Private profile fields and conversations are not public.

## Sources and precedence
The [English overall concept](overall-concept-en.md) faithfully translates the original document and remains background material. Its old stack, fixed deck size and gameplay proposals are not current implementation instructions. The [original brief](archive/product-brief-original.md) and older specifications are retained under archive. Later user-approved named specifications take precedence for their topic; unresolved future rules require group review.
