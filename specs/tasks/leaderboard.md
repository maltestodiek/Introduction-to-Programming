# Leaderboard

Parent topic: [Battle Mode](../battle-mode.md), which owns Battle XP. Friendships come from [Social connections](../social-connections.md); navigation and layout follow [Appearance and navigation](../appearance-and-navigation.md).

## Why

Students want to see how their Battle results compare with others. A small, fair ranking gives Battle Mode a visible goal without turning the ranking into a way to collect contacts.

## What

The Leaderboard tab shows two rankings. Both are built only from Battle XP, the XP earned from Battle results. Study Mode, study plans and learning progress never change them.

- Global: the ten students with the most Battle XP. If the signed-in student is not among them, their own place is shown as an eleventh row below the ten, with its real place number.
- Friends: the signed-in student together with their accepted friends, ranked among themselves.

Every row shows the place, the profile picture or avatar, the username and the XP. The student's own row is marked. Students with the same XP share the same place; within a place the order is alphabetical by username.

The leaderboard is read-only. It offers no friend code, no invitation, no chat and no link to a profile, so being at the top does not expose a student to unlimited requests. It returns only what signed-in students can already see about each other: username, picture and XP.

For development, a local copy (APP_URL on localhost) can set LEADERBOARD_DEMO to 1 to show invented students instead of the real ranking, with a visible notice. The switch is ignored anywhere else and never reads or writes the database.

State and persistence: nothing new is stored. The rankings are read from the existing profile XP each time the tab is opened.

## Out of scope

Any XP value other than Battle XP or Total XP in the ranking, rankings per course or university, weekly or seasonal rankings, rewards, more than ten global places, searching for a student, and any action on another student from the leaderboard.

## Done when

1. Allowed: a signed-in student opens Leaderboard and sees the global top ten with place, picture, username and XP, and their own row marked.
2. A student outside the top ten sees the ten rows plus their own row with its real place; a student inside the top ten sees exactly ten rows.
3. Students with equal XP share a place, and the next place skips accordingly.
4. The friends ranking contains only the student and their accepted friends; pending requests and strangers are not included. A student without friends sees only themselves and a hint to add friends.
5. Rejected: an anonymous caller gets nothing; a signed-in student without a profile gets an error and no data.
6. Privacy: the response contains only place, username, picture path, XP and the own-row mark. It has no friend codes, emails, courses or invitation data, and the screen offers no invite or chat action.
7. A Study session or study plan activity does not change any place; a settled Battle result does.
8. Restart: the ranking is the same after a full restart, because it is read from stored XP.

Checks: `tests/test_leaderboard_ui.py` and `tests/leaderboard_database.mjs`.
