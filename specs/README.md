# Feature specifications

Each active specification uses the lecture structure: **Why, What, Out of scope, Done when**. Features are named by product responsibility, not implementation order.

- [Authentication and student profiles](authentication-and-profiles.md): account access, recovery, profile data, avatar/photo and verified session restoration.
- [Social connections](social-connections.md): friend codes, invitation links, requests, chat and participant actions.
- [Deck authoring](deck-authoring.md): editable decks, subsections, review, question calculator and import placeholders.
- [Study Mode and learning progress](study-mode.md): solo/together sessions, matching, levels, feedback, notes and earned copies.
- [Battle Mode](battle-mode.md): future competitive rules and the boundary around existing classic duels.
- [Appearance and navigation](appearance-and-navigation.md): branding, dark/light themes, backgrounds, icons, animations, page layout and history navigation.
- [Basic Anki text-card import](tasks/basic-anki-import.md): private import of up to 100 text-only Basic Anki notes.
- [Text from images on Anki cards](tasks/anki-image-text.md): read the text on Anki card images with AI, review it and import it as text cards.
- [AI question generation](tasks/ai-question-generation.md): private, server-side Requesty generation of reviewed MC drafts from imported source cards.
- [Question notepad](tasks/question-notepad.md): unsaved 500-character scratch notepad beside the calculator during questions.
- [Leaderboard](tasks/leaderboard.md): global top ten with own place and a friends ranking, by Battle XP, read-only.
- [Battle round layout](tasks/battle-round-layout.md): active-round overview and server-timed countdown display.
- [Battle question reports](tasks/battle-question-reports.md): participant reports for individual completed-Battle questions.
- [Battle invitation badge](tasks/battle-invitation-badge.md): pending incoming Battle invitations shown next to Play.
- [Battle Deck availability](tasks/battle-deck-availability.md): confirm an eligible public Battle Deck exists before random matchmaking starts.
- [Study round layout](tasks/study-round-layout.md): active-round overview without a per-question timer.
- [Profile button avatar](tasks/profile-button-avatar.md): the header Profile button shows the user's own picture instead of an icon and a separate portrait.
- [Friends header button](tasks/friends-header-button.md): Friends moves from the large tabs into the header between Profile and Chats.
- [Play landing page and logo button](tasks/play-landing-and-logo.md): sign-in lands on Play, and the header logo opens Play.
- [Start a chat from the friend list](tasks/friend-list-chat.md): clicking a friend on the Friends page opens the private conversation.
- [Friends dashboard layout](tasks/friends-dashboard-layout.md): a scannable Friends and invitation layout without changing social rules.
- [Calculator result rounding](tasks/calculator-rounding.md): the question calculator shows results rounded to four decimal places, with a note saying so.
- [Arena logo](tasks/arena-logo.md): the two flashcards stand in an arena.
- [University, field-of-study and course selectors](tasks/study-fields-and-shared-courses.md): type-ahead university search, field of study from a list of common degree subjects, and a course selector that lists courses already saved at the student's university.
- [Profile figures beside the avatar](tasks/profile-stats-beside-avatar.md): Battle XP, Win streak and Friends as a compact row next to the avatar.
- [Faster page loads](tasks/faster-page-loads.md): smaller images, reused profile data and pictures, fewer sign-in checks and slower inbox polling.
- [Play sessions dashboard](tasks/play-sessions-dashboard.md): continue banner, ongoing session grid, history table and Battle/Study figures on Play.
- [Deck studio](tasks/deck-studio.md): own Study and Battle decks with status, creation/edit/publication times and edit or publish actions.
- [Study plan with Google Calendar](tasks/study-plan.md): plans per course with daily workload, progress, today's sessions and calendar sync.
- [Study Plan desktop layout](tasks/study-plan-desktop-layout.md): wide overview and editor layout without changing Study Plan behaviour.
- [Course list on Decks](tasks/course-list-layout.md): desktop course overview with Study access plus a searchable, filtered deck catalogue.
- [Immersive round interface](tasks/immersive-round-ui.md): start countdown, answer-feedback effects, streak display and equal card heights in Battle and Study rounds.
- [Unsaved-creation warning](tasks/unsaved-creation-warning.md): a confirmation modal before unsaved deck-creation content is discarded in the manual editor and both imports.
- [Full-height sidebar](tasks/full-height-sidebar.md): the desktop navigation runs as a continuous bar along the left edge instead of a floating card.

A feature can require several small implementation branches. Add a task spec under `specs/tasks/` when a change needs its own acceptance scenarios; link it to its parent topic. Do not duplicate a rule across multiple feature specs. Before implementation, list state, persistence, an allowed action, a rejected action and restart verification; review expected outcomes with the group.

Older proposals are preserved under [docs/archive](../docs/archive/README.md). They record history and do not override the active specs. The initial numbered filenames have been retired.
