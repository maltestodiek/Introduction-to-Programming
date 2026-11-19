# Battle Deck availability

## Why

Students should not wait in random matchmaking when no public 15-question Battle Deck can satisfy their selected course and language.

## What

Before a Random Deck search or random Deck friend invitation is created, verify on the server that an eligible public Battle Deck exists for the signed-in student's university, selected course and selected language. The Battle setup screen shows an English explanation and disables the relevant action if none is available.

When an eligible deck exists but no compatible random opponent is immediately available, confirm that the search runs for up to one hour and show it in the Game Overview's Pending column. Show a live `HH:MM:SS` countdown. Poll the server status so a newly found opponent moves the user to Ongoing without a manual reload. The player can cancel their own pending search. At expiry, remove the search and its Pending card automatically. The stored search must remain visible after an application restart until it expires.

## Out of scope

- Changing eligibility rules, the one-hour search duration, friend relationships, notifications, or Top Deck ranking.
- Creating a Battle Deck automatically when none exists.

## Done when

1. A student cannot create a Random Deck search or invitation without an eligible Battle Deck, including by bypassing the UI.
2. The setup screen clearly explains the missing-deck state and disables the random matchmaking action.
3. A successful unmatched Random Deck search confirms its one-hour duration, appears under Pending, and counts down live.
4. A player whose opponent is found sees the search disappear and the Battle appear under Ongoing without manually reloading.
5. A player can cancel only their own pending search.
6. At zero the server removes the expired search and the Pending card disappears.
7. Restarting the app preserves the pending-search display until it expires.
8. Isolated database and Streamlit UI tests cover the allowed and rejected flows.
