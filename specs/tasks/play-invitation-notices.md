# Play invitation notices

Parent topics: [Appearance and navigation](../appearance-and-navigation.md), [Social connections](../social-connections.md), [Battle Mode](../battle-mode.md), and [Study Mode](../study-mode.md).

## Why

Students should notice pending invitations as soon as they open Play, without adding controls or changing the existing invitation workflows.

## What

The initial Play landing page shows a read-only notice below the Battle Mode card for each pending incoming Battle invitation and below the Study Mode card for each pending incoming Study invitation. A notice identifies the invitation type, deck when available, sender and course. The first Battle notice shows the total incoming-Battle invitation count, matching the left Play-navigation badge. The Battle notice group includes one **Open Battle Mode** button that opens the existing Battle overview, where the established invitation workflow remains available. Notices have no accept/decline controls or read state.

## Out of scope

Browser push notifications, persisted read/unread state, outgoing invitations, matching rules, invitation authorization, or accepting and declining invitations from the Play landing page.

## Done when

1. Incoming pending Battle and Study invitations appear as clearly marked read-only notices below their respective mode cards.
2. Outgoing Battle invitations do not produce a landing-page notice.
3. Battle notices offer only the navigation action to the existing Battle overview; notices have no accept/decline controls and disappear when the server no longer returns the invitation.
4. Existing Battle Mode and Study Mode invitation actions remain unchanged.
