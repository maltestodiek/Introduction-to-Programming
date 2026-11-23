# Study plan with Google Calendar

Parent topic: [Study Mode and learning progress](../study-mode.md), which owns learning levels and Study sessions. Navigation and layout follow [Appearance and navigation](../appearance-and-navigation.md).

Status: implemented on branch feature/study-plan. The connection to a real Google account is not yet verified manually.

## Why

Students prepare for several exams at once and need to know how many questions to study each day to be ready in time. A plan that divides the work over the available days, shows progress per course and puts the sessions into the student's own calendar turns the existing decks and learning levels into a schedule they can follow.

## What

### Creating a plan
The Study Plan tab lists the student's plans and offers Create study plan. A student can have several plans. A plan applies to Study Mode only.

A plan contains one or more courses. Only courses from the student's profile can be added. For each course the student sets:

- a target date for each course, the last day the student wants to study. Sessions may be scheduled on that date;
- a start date, shown next to the end date: today by default (start right away), or a later first study day before the end date; it can be changed whenever the plan is edited;
- the decks to study, chosen from the decks available to them for that course: their own decks and copies earned by studying with friends.

For the whole plan the student sets:

- the target learning level (1, 2 or 3) that every question in the plan should reach, shown with the level colours and an info legend explaining the levels;
- the study days: no weekly days off by default; weekdays can be excluded (for example weekends) and single dates can be excluded;
- 1, 2 or 3 sessions per study day, with a short explanation that a session is one sitting in Study Mode;
- a start time for each session. The app suggests 09:00, 14:00 and 19:00; the student can change them before saving.

### Daily workload
Reaching a level takes one correct answer per level step, so the workload counts steps, not questions. For each course:

- remaining steps = for every question, target level minus current level, never below zero (a new or level-0 question needs the full target);
- steps per study day = remaining steps divided by the study days left until that course's end date, rounded up;
- the whole plan has at least 20 steps on every study day: a day below 20 is topped up with later steps, taken first from the course that ends soonest; when fewer than 20 steps remain in the plan, all of them are planned for one day;
- steps per session = steps per study day divided by the sessions per day, rounded up.

Because of the 20-per-day minimum a course can be finished before its end date. Before saving, the plan shows for each course the questions per day and per session, the number of study days it takes, and the day the student will be done, including how many days that is before the target date. The workload is recalculated from current progress each day, so a missed day or wrong answers spread the remaining work over the days left. A plan whose end date has passed is shown as ended with its final progress.

### After saving
Saving a new or edited plan opens a short step for that plan: it repeats the workload, offers the calendar file and Add to / Update Google Calendar, and has a Finish button. Finish leads to the overview with the progress of every plan. From the overview the student can still create further plans and edit or delete existing ones, and the calendar actions stay available there.

### Today's sessions
Each saved plan shows today's sessions at full width above course progress. Long session button labels wrap so the action, course and question count are readable on narrow screens. Today's sessions (named Morning, Afternoon or Evening by their start time) have a start button for everything still open, per course. Starting one opens a solo Study session with questions below the target level from the plan's decks. The same open to-dos are listed on Play with the ongoing Study sessions.

The amount for today is fixed the first time the plan is opened that day. Answers given during the day fill the sessions in order, and a finished session is marked as done. A session can be done at any time of the day, also late in the evening; nothing is added or moved while the day is running. Only what is still open after the day is over is spread over the remaining study days.

### Overview and editing
The overview shows for each plan only its name, the progress of each course (and overall progress for several courses), today's sessions and an Edit button. Calendar file, Google Calendar and Delete are in the editor of a saved plan. Deleting asks for confirmation for that one named plan.

### Progress
Course progress = sum over its questions of min(current level, target level), divided by questions times target level. Example: all questions at level 1 with target 2 is 50%. Plan progress uses the same formula over all questions of all its courses. The Study Plan tab shows each plan with its overall percentage and, when it has more than one course, one percentage per course. Progress reads the existing learning levels; the plan never changes them.

### Google Calendar
Google Calendar sync is currently limited to registered Google test accounts. Show this beneath each Google Calendar action and repeat it when opened. Offer Google sign-in as a separate step for testers when configured. Everyone can download the calendar file. A saved plan offers Add to Google Calendar. The student signs in with Google and grants permission to manage calendar events. The app then creates one event per planned session (title with course and question count, start time, and a length of 15 seconds per question step, at least 15 minutes) in the student's primary calendar and remembers which events belong to the plan.

- The app requests only the calendar-events permission and uses it only at the moment of syncing. It does not keep a long-lived Google token; a later sync asks Google again.
- Editing a plan changes nothing in the calendar until the edit is saved. After saving an edited plan that was added to the calendar, the student confirms Update Google Calendar; the app then deletes or changes the plan's old events and creates the new ones.
- Deleting a plan offers to remove its events from the calendar.
- The app only touches events it created for that plan.
- Students who do not use Google can download the same sessions as a calendar file (.ics).

State and persistence: plans (courses, end dates, decks, target level, excluded days, sessions, times) and the identifiers of created calendar events are stored per student in Supabase and are private to that student. Google client credentials live only in the hosting secrets.

## Out of scope

Plans for Battle Mode or classic duels, shared or group plans, reminders or notifications sent by the app, reading the student's other calendar events or avoiding conflicts with them, Outlook or Apple sign-in, automatic background syncing without the student present, and changes to learning-level rules.

## Done when

1. Allowed: a student creates a plan with two profile courses, different end dates, selected decks, target level 2, weekends excluded and two sessions per day, and sees the questions per day and per session for each course.
2. Rejected: a course that is not in the profile, a deck of another course or one the student cannot access, an end date in the past, a plan without decks or with no study day left cannot be saved; nothing is stored.
3. Workload: with 30 new questions, target level 2 and 10 study days left, the plan shows 20 per day on 3 study days and that the student is done 7 days before the target date. With 300 new questions it shows 60 per day on 10 study days; after a missed day the remaining steps are spread over 9 days. With 12 steps left, all 12 are planned for one day. A later start day moves the first session to that day.
4. Progress: all questions at level 1 with target 2 shows 50%; levels above the target count as the target; a two-course plan shows both course percentages and the overall percentage.
5. Calendar: after Add to Google Calendar the student's calendar contains exactly the planned sessions at the chosen times. Opening Edit and leaving without saving changes nothing. Saving an edit and confirming the update removes outdated events and adds the new ones; events not created by the app are untouched.
6. Privacy: another student cannot read or change the plan or its event identifiers. No Google token is stored in the database or the repository.
7. Restart: plans, settings and progress survive a full restart and a new sign-in.
8. The calendar file download contains the same sessions as the plan.

Checks: `tests/test_study_plan.py` (rules), `tests/test_study_plan_ui.py` (screens), `tests/test_google_calendar.py` (Google requests, simulated) and `tests/study_plan_database.mjs` (isolated database). Item 5 against a real Google account is a manual check.

## Open points for the group

- Google setup: the direct connection needs a Google Cloud project with the Calendar API, an OAuth client and its secrets in hosting. While that project is in Google's testing mode, only Google accounts added as test users can connect (at most 100), and users see an unverified-app notice. Public use requires Google's verification.
