# Battle Deck availability

## Why

Students should not wait in random matchmaking when no public 15-question Battle Deck can satisfy their selected course and language.

## What

Before a Random Deck search or random Deck friend invitation is created, verify on the server that an eligible public Battle Deck exists for the signed-in student's university, selected course and selected language. The Battle setup screen shows an English explanation and disables the relevant action if none is available.

When an eligible deck exists, open the random Battle immediately and use the search and resume rules in the [Battle specification](../battle-mode.md#eligibility-and-matching).

## Out of scope

- Changing eligibility rules, friend relationships, notifications, or Top Deck ranking.
- Creating a Battle Deck automatically when none exists.

## Done when

1. A student cannot create a Random Deck search or invitation without an eligible Battle Deck, including by bypassing the UI.
2. The setup screen clearly explains the missing-deck state and disables the random matchmaking action.
3. Start immediately with an eligible deck. An unmatched round appears in Active battles after reopening the app.
4. A compatible second player receives the same frozen questions and their own finish deadline.
5. Cancelling or expiring an unmatched search produces no result or XP.
6. The database and Streamlit checks exercise both immediate starts and rejections.
