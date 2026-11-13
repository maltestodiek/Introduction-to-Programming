# Feature specifications

Each active specification uses the lecture structure: **Why, What, Out of scope, Done when**. Features are named by product responsibility, not implementation order.

- [Authentication and student profiles](authentication-and-profiles.md): account access, recovery, profile data, avatar/photo and verified session restoration.
- [Social connections](social-connections.md): friend codes, invitation links, requests, chat and participant actions.
- [Deck authoring](deck-authoring.md): editable decks, subsections, review, question calculator and import placeholders.
- [Study Mode and learning progress](study-mode.md): solo/together sessions, matching, levels, feedback, notes and earned copies.
- [Battle Mode](battle-mode.md): future competitive rules and the boundary around existing classic duels.
- [Appearance and navigation](appearance-and-navigation.md): branding, dark/light themes, backgrounds, icons, animations, page layout and history navigation.

A feature can require several small implementation branches. Add a task spec under `specs/tasks/` when a change needs its own acceptance scenarios; link it to its parent topic. Do not duplicate a rule across multiple feature specs. Before implementation, list state, persistence, an allowed action, a rejected action and restart verification; review expected outcomes with the group.

Older proposals are preserved under [docs/archive](../docs/archive/README.md). They record history and do not override the active specs. The initial numbered filenames have been retired.
