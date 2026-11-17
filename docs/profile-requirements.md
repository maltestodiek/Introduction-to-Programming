# Account and profile requirements

Confirmed with the group on 11 November 2026. All screens and documentation are in English.

## User journey

Create account with email, password, and unique username. Confirm the email, sign in, then complete university, course, and language selections. Choose an optional uploaded photo or custom avatar. Save the profile and open it. Returning users can edit their profile details. A partially completed profile returns to setup after the next login.

## Identity and visibility

Email is private and used for authentication. Passwords are handled by Supabase Auth and never shown or stored in application tables.

Username is visible to other signed-in users. Enforce uniqueness without case-sensitive duplicates. If a chosen username becomes unavailable before profile creation, ask the student to choose another; do not strand an otherwise valid account.

University is required, editable, and visible to signed-in users. Courses require at least one selection and are private by default; they personalize course browsing. Languages require at least one selection, are editable, and are visible to signed-in users. These are spoken/preferred languages, not a promise of a translated interface.

Use catalog selections for universities, courses, and languages. The existing three prototype courses are Financial Modeling, Corporate Finance, and Investments. The university catalog and course-to-university mapping must be supplied or explicitly labeled as prototype sample data; do not claim those courses belong to every university. Changing university must ask the user to review any incompatible course selections.

No public anonymous profile page is required. 'Visible' means visible inside StudyDuel to signed-in users. Profile editing is restricted to its owner. Do not expose private course selections or email through a public profile response, even if hidden by the interface.

## Profile image

Offer two modes:
- Upload a photo, preview it, and crop it before saving.
- Create an avatar with skin tone, hairstyle, hair color, clothing color, and accessories such as glasses or a hat.

Image selection is optional. Skipping it uses a default avatar. Users can customize later or switch modes. Only one image mode is active at a time.

Store the uploaded photo and avatar configuration privately. Other signed-in users can see the selected profile image, but cannot retrieve raw customization settings, inactive uploads, or the original uncropped image. Proposed implementation: crop and remove metadata before uploading; retain only the cropped result. Render custom avatars deterministically from allowed preset values.

The selected image will be reused on profiles, deck authorship, duels, friends lists, and the leaderboard as those features are built. These screens are now implemented under their named feature specifications.

Reject invalid image files with a helpful message and preserve the current profile image. Proposed upload defaults: JPEG or PNG, maximum 5 MB; verify actual image contents rather than trusting the extension. Persist the active image selection and avatar settings so they survive sign-out and restart. A failed save must leave the last confirmed selection intact.

## Information earned or managed later

Show 0 XP, a 0 win streak, and an empty friends list for a new account. XP and win streak are visible to signed-in users and cannot be edited through profile settings. Future duel rules calculate them.

The friends list is private to its owner, and each friendship is visible to the two people involved. Friendship creation/removal is owned by Social Connections; a new profile starts with an empty friend list.

## Persistence and access boundaries

Supabase Auth stores account identity. Profile records and images belong in Supabase Database and Storage so they are available to the same user across devices. This extends the prior SQLite-only application data plan for this feature; SQLite is not an identity or profile-image store.

Require owner-based database and storage access rules and an explicit limited representation for other signed-in users. Session state alone is not a durable profile. After a restart, Supabase verifies any restored session before loading the saved profile; otherwise the user signs in again. Authorization must not depend on user-editable metadata or an editable XP field.

## Acceptance scenarios

1. A new confirmed account completes university, courses, and languages and saves a profile. Skipping the image displays a default avatar and zero XP/streak with no friends.
2. Save a customized avatar. Sign out and back in, then restart and sign in again. All saved profile details and avatar choices remain.
3. Upload and crop a valid photo, save it, then switch back to a customized avatar. Exactly one chosen image is displayed everywhere the profile is used.
4. Invalid uploads, missing required selections, duplicate usernames, or failed saves show a useful error and preserve the previous saved profile.
5. User A can edit their profile. User B cannot edit A, access A's email, courses, inactive photos, or raw avatar settings. B can view A's allowed username, university, languages, selected image, XP, and streak. Anonymous requests cannot read either profile.
6. Profile updates cannot modify earned XP, streaks, or friendship records.

## Profile refinements agreed on 11 November 2026

Username guidance appears below the field. Invalid input is highlighted in red beside the username; failed submission preserves all entered values so the student can correct only the problem. Password fields clear after successful authentication/signup, not after validation failure.

The avatar editor offers category tabs and sideways swipe, arrow, keyboard, and dot controls with immediate character previews, eight skin colors including blue/green/purple/pink, ten hairstyles, and ten accessories plus None. Previous saved avatar options remain supported.

Universities and courses can be entered manually when absent from the starter catalog. Live worldwide search uses the ROR v2 API with the education filter and displays institution names with countries. Only the search text is sent to ROR. Missing institutions can be entered manually, including during an API outage. ROR is not a complete university/department directory.

Optional degree level and field of study are editable, saved privately, and reserved for later matching. Courses remain private. Later shared course discovery will list university-scoped course names, not enrollment identities. Catalog moderation, aliases and duplicate merging will need rules before that shared feature is built.

The former tests rejecting every unknown university/course were updated to reject blank names instead, reflecting the user's explicit custom-entry requirement.

UI refinements: University selection opens a dropdown with search first, selectable results, and manual entry. The prototype option and ROR detail link are removed. Skin labels use Light, Tanned, Coloured, Blue, Green, Purple, Pink, and Gold. Existing stored skin identifiers stay unchanged to preserve saved avatars.

Profile study fields appear in this order: university, degree level, field of study, courses, languages.

Profile summary: show the individual friend code in muted grey beside the username. Display degree and field together beneath the university (for example, Master in Finance). Render the avatar at full source resolution, sized only by CSS, to avoid blurry downsampling.


## Expected graduation year
Expected graduation year is optional (2000–2100), owner-private, editable and removable. The summary shows Class of YEAR beneath the university beside the degree. It does not infer academic year without a program start date. Apply supabase/graduation-year.sql before deploying this version.
