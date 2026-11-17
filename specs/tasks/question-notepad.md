# Question notepad

Parent topics: [Study Mode](../study-mode.md) for the session behaviour and [Appearance and navigation](../appearance-and-navigation.md) for the layout. The calculator it sits beside is defined in [Deck authoring](../deck-authoring.md).

## Why

Students often need to jot down an intermediate step, a formula or a guess while answering a question. A scratch notepad next to the calculator lets them do that without leaving the question, and without creating stored notes that could leak an answer into a later attempt.

## What

Every active question in a Study session and in a classic duel round offers a Notepad button beside the Calculator button. When a question does not allow the calculator, the Notepad button is still offered on its own.

Opening the notepad shows a small panel with one text field of at most 500 characters. On desktop the panel sits on the right, directly below the calculator when both are open, so the question, the calculator and the notepad are visible together without scrolling the page. Only the text inside the field scrolls when it is longer than the visible area. On narrow screens the panel is shown inline at full width.

The notepad is scratch space for one attempt at one question:

- State: the text and the open/closed flag live only in the browser session.
- Persistence: none. The text is never sent to the database, never stored with the private note or author feedback, and never shown to a partner.
- It is empty and closed when the next question appears, when the same question is answered again, and after a restart or new sign-in.
- Closing and reopening the notepad during the same attempt keeps the text.
- Typing never submits an answer, changes progress or pauses a duel timer.

## Out of scope

Saved or shared notes, formatting, images, a notepad on the feedback screen, changes to the existing private note / feedback to author feature, and changes to calculator permissions or arithmetic.

## Done when

1. Allowed action: on a question, a student opens the notepad, types up to 500 characters, closes and reopens it and still sees the text. No answer is submitted and no repository call carries the text.
2. Rejected action: text beyond 500 characters is not kept.
3. After answering, the notepad for the next question, and for the same question when it is asked again, is closed and empty.
4. The notepad is offered with and without calculator permission, in Study and in classic duel rounds, and can be open together with the calculator.
5. Restart: after a full restart the notepad is empty, because nothing was stored.
6. Visual check in the running app: on a desktop window the question, calculator and notepad are all visible without page scrolling, in light and dark themes.

Checks: `tests/test_notepad.py`. Item 6 is a manual check.
