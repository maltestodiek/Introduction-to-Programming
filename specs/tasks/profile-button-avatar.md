# Profile button avatar

Parent topic: [Appearance and navigation](../appearance-and-navigation.md).

## Why

The header showed the user's picture twice in effect: a separate portrait beside the Profile button, and a generic person icon inside it. One control that carries the user's own picture is clearer and frees header space.

## What

The header Profile button shows the signed-in user's current profile picture (rendered avatar or uploaded photo) as a small circle before the "Profile" label. The generic person icon is removed from the button, and the separate portrait beside the button is removed from the header. Users without a saved picture see the default avatar. The picture is small enough (28 px) that the button keeps the height of the neighbouring Chats control. The button keeps its label, click target, hover/focus styling and reduced-motion behaviour, and still opens the Profile page.

## Out of scope

Changing the avatar character design, the stored picture, photo upload rules, the portraits on the Profile page, chat, friends or leaderboard, or any database rule.

## Done when

1. The header contains no standalone profile portrait next to the Profile button.
2. The Profile button's leading artwork is the user's own picture, not a mask icon.
3. A user without a saved picture sees the default avatar in the button.
4. Clicking the button still opens the Profile page.

Checks: `tests/test_profile_button.py`, plus a manual look in the running app in light and dark themes.
