# University, field-of-study and course selectors

Parent topic: [Authentication and student profiles](../authentication-and-profiles.md). Profile field rules: [profile requirements](../../docs/profile-requirements.md).

## Why

Students typed their field of study and their courses freely. Two students in the same course could save different spellings, so decks, Study and Battle would not match them. New students also faced an empty course list.

## What

### Field of study
Field of study is chosen from a searchable list of about 160 common university degree subjects under the names students use for them, for example "Business Administration", "Finance", "Computer Science" or "Law". The list is a convenience, not a closed set: a student can still type a field that is not listed, and a previously saved value stays selectable. The field remains optional and private.

An official classification (UNESCO's ISCED-F) was tried first and set aside, because its field names do not match everyday degree names: Business Administration, for example, appears there only as "Management and administration".

### University
University is a type-ahead field. While the student types, suggestions appear under the field: first the universities UniArena students already use that contain the typed text, then the matching institutions from the worldwide ROR directory, searched live. Picking a suggestion sets the university. A final entry keeps the name exactly as typed, for institutions the directory does not know.

The directory is searched from the student's browser, so suggestions appear without reloading the form; only the typed text is sent to ROR, never account details. If the student confirms a typed name without picking a suggestion, the server also looks it up and offers the official names under the field, as before; the typed name is kept if none is chosen, nothing is found, or the directory cannot be reached. Arrow keys, Enter and Escape work in the suggestion list.

The list of universities in use is read from the university field of saved profiles, which signed-in students can already see on each other's profiles.

### Courses
The course selector on the profile form lists every course name that students at the chosen university have already saved, together with the student's own courses. A missing course can still be typed; once saved, it appears for other students at that university.

Names are matched without regard to letter case or repeated spaces. If a typed name matches a listed course, the listed spelling is saved, so students in the same course hold the identical name. When several spellings of one course already exist, the list shows the most used one.

### Adding courses from the profile
The profile page has an Add courses button under Your courses, in place of the former Open friends button (Friends is reached from the header). It opens the same course selector as Edit profile, with Save courses and Cancel. Saving changes only the courses; username, university, languages, image and study details are saved back unchanged. At least one course must remain.

State and persistence: no new table. Supabase reads the names from the saved profiles through the `university_courses` function. It returns course names only for the requested university, never usernames, user ids or how many students take a course. Only signed-in students can call it.

Privacy note: a student's own course selection stays private, but the names in use at a university are visible to signed-in students. At a university with a single student, those names are that student's courses.

## Out of scope

Moderating, renaming or merging course names; course codes; a course catalogue supplied by universities; changing who can see decks; matching rules in Study and Battle.

## Done when

1. The field-of-study selector offers common degree subjects such as Business Administration, accepts a typed field and keeps a previously saved value.
2. The course selector lists courses saved by other students at the same university and none from other universities.
3. A course typed with different letter case or spacing is saved with the listed spelling, without duplicates.
4. Anonymous callers cannot read the course list; the result contains names only.
5. If the course list cannot be loaded, the form still works with the student's own courses and typed entries.
6. Typing in the university field shows matching universities in use and from the ROR directory; a picked suggestion is saved as shown, and a typed name is kept when no match is chosen.
7. Add courses on the profile opens the same selector, saves only the courses, rejects an empty selection and can be cancelled.

Checks: `tests/test_course_catalog.py`, `tests/test_profile_summary.py`, `tests/university_courses_database.mjs`, `tests/test_ui.py`, plus manual checks: the live suggestions in a browser (they run in the browser and are not covered by the automated tests), and two accounts at one university.
