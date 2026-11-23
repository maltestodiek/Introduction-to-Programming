# Study Plan desktop layout

Parent topics: [Study Mode and learning progress](../study-mode.md) and [Appearance and navigation](../appearance-and-navigation.md).

## Why

Students need to understand today’s work, overall course progress and how to adjust a plan without changing the planning rules that already organise their learning.

## What

Arrange the existing Study Plan overview and editor as a wide desktop workspace: the overview pairs course progress with today’s sessions, the empty state explains the existing setup flow, and the editor groups courses, goal and weekly settings beside a live read-only workload preview.

Editor details: each selected course is one compact row with its decks and target date under the column labels Course, Decks and Target date, and a collapsed **Start later (optional)** section for a later start date. The three goal levels are cards with a colour bar; the whole card selects the level, Level 2 is marked Recommended. Study days are compact round toggles, and the 1, 2 or 3 sessions per day sit in one row with their start times. While the plan cannot be saved yet, the preview lists **To save this plan** with a check for each step (name, at least one course, decks for every course, target date for every course) above the precise reason. Once valid it shows the live workload preview and a note that sessions can be added to Google Calendar after saving. The Save study plan button stays fully readable.

State and persistence remain the existing private Study Plan record, calendar-event identifiers and current learning levels. The change adds no state or persistence.

## Out of scope

Changing the scheduling algorithm, learning-level rules, plan payload, Google Calendar workflow, notifications or Study session behaviour.

## Done when

1. Allowed: creating, saving, editing, starting today’s session, exporting a calendar file and opening Google Calendar use the same actions and data as before the layout change.
2. Rejected: an invalid plan remains unsaveable and changing editor controls without saving changes neither the stored plan nor calendar events.
3. Restart: a saved plan, its progress and today’s open or completed sessions still appear after a new sign-in.
4. The overview is readable on a wide screen with progress and today’s sessions side by side, while the editor keeps all existing labelled inputs and adds only a read-only live preview.

Checks: `tests/test_study_plan.py`, `tests/test_study_plan_ui.py`, `tests/test_study_plan_editor_layout.py`, `tests/test_google_calendar.py` and a manual desktop visual check.
