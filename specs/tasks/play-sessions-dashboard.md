# Play sessions dashboard

Parent topic: [Appearance and navigation](../appearance-and-navigation.md).

## Why

Ongoing sessions and history were two equal Battle/Study columns of large cards. Students could not see at a glance what to do next, whose turn it is or how they are doing.

## What

Play starts directly with the Battle and Study mode cards; it has no separate "Create new session" heading or introductory sentence. Below the cards, **Your sessions** shows All, Battle and Study filters and two columns. The filters align to the right edge of the Study card and use the same rounded primary-button visual language as the Study Mode action.

The main column starts with a **Continue where you left off** banner for one session: a Together Study session with the nearest deadline (with the time left), otherwise a Battle where it is the player's turn, otherwise a Study session to resume. Its Resume button does exactly what the session's own resume button does. **Ongoing sessions** follow as a two-column grid of cards with progress, a turn badge (Your turn, Opponent's turn, Ready to start, Waiting for a study partner), the partner menu for Together sessions, deadlines and the existing Start/Resume Battle and Open/Resume Study actions. **Session history** is a table with Result, Deck, Mode (opponent or Solo/Together with the partner menu), Score and XP plus the existing Review Battle and View Study session actions; it shows five rows and Show more adds ten.

The side column shows the Battle record (wins – losses, with a bar), Battle XP from the listed Battles, finished Study sessions with answered questions, the profile's win streak and the existing Study plan to-dos.

Only stored data is shown. Sessions have no stored finish date and Study sessions no stored accuracy, so the table has no Date column and the figures use counts instead of weekly XP or accuracy.

## Out of scope

New session data (dates, accuracy, weekly XP), Battle or Study rules, and a separate New session button (the creation area above already starts sessions).

## Done when

1. The continue banner, ongoing cards and history rows trigger the same actions as before: Battle sessions open with their id, Study sessions resume with their mode, and history opens Battle review or the Study session.
2. Filters show only Battle or only Study sessions in the banner, grid and history.
3. Turn badges match the session state, and history results show Win, Loss, Draw, Done or Expired.
4. History shows five rows first and more on request; empty states invite starting a session.
5. The page works in light and dark themes, keeps the mode-card creation area above the dashboard without redundant introductory copy, and aligns its filters with the card layout.
