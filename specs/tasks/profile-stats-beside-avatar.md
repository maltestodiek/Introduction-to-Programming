# Profile figures beside the avatar

Parent topic: [Appearance and navigation](../appearance-and-navigation.md). Figures and visibility: [profile requirements](../../docs/profile-requirements.md).

## Why

Total XP, Win streak and Friends took a full row of large cards under the avatar and pushed the rest of the profile down, although they are three small numbers.

## What

The profile shows Total XP, Win streak and Friends as a compact row beside the avatar, directly under the username and friend code. Each figure is a number with its label. Total XP keeps its Game XP and Creator XP breakdown in small text. The three large cards under the avatar are removed. If the friends list cannot be loaded, Friends shows a dash. On a narrow screen the row wraps.

## Out of scope

How XP, streaks and friendships are earned or stored; who may see them; the rest of the profile page.

## Done when

1. The figures appear beside the avatar, under the username, and not as cards below it.
2. Total XP still shows its Game XP and Creator XP parts.
3. Friends shows a dash when the friends list is unavailable.

Checks: `tests/test_profile_summary.py`, `tests/test_profile_changes.py`, plus a manual look in both themes.
