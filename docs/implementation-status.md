# First feature implementation status

Implemented on first-feature, 11 November 2026. Not committed, pushed, merged, or deployed.

## Verification
- 32 pytest checks passed in the Desktop project (32 passed in 3.56s), including existing authentication acceptance tests, profile validation, image processing, storage failures and Streamlit UI checks.
- Live SQL transactions verified owner reads, owner-only private data, denied cross-user profile writes, XP column protection, case-insensitive username uniqueness, anonymous denial and rollback of failed saves.
- Authentication email/password and email confirmation are enabled.
- Confirmation Site URL is http://localhost:8501.
- No service-role key is used.

Live signup email delivery, confirmation, full user round-trip and saved-profile recovery after process restart still need a real user walkthrough. Tests do not send email. Avatar/photo UI is implemented; storage endpoint behavior with real user credentials needs that walkthrough.

- Browser verification: app loads, malformed email rejected, Create account displays username/email/password/confirmation.
- Live Storage policy checks: only the selected image was visible to a second user; uploads into another user’s folder were rejected. SQL test rows were rolled back. Storage deletion must be tested through its API; Supabase blocks direct SQL deletion.
- The app is running locally at http://localhost:8501. No deployment or GitHub push was performed.

## Profile refinement verification

35 tests passed in 2.80s after adding regression tests for preserving signup inputs, username guidance, ten distinct hairstyles, ten accessories plus None, playful skin colors, and custom study fields. Unknown university/course rejection expectations were explicitly revised to blank-name rejection per the user's new requirements. ROR directory integration and shared university-scoped course search are planned, not implemented.


## Friends release — 11 November 2026
- Supabase-backed stable friend codes, recipient-approved requests, sender cancellation, mutual friendships and removal.
- Seven-day revocable/rotatable invitation links, explicit acceptance, signup continuation, and user-initiated sharing.
- 62 Python checks passed. Both SQL acceptance scripts passed against synthetic identities under authenticated/anonymous roles and rolled back all test data.
- Local browser preview verified acceptance changes the count/list, code placement, degree subtitle, and native-resolution profile artwork. No real invitation messages were sent.
- Real two-person email-confirmation/acceptance remains a user walkthrough; automated checks do not create real accounts or send email.
- Profile skin label updated to Coloured at the user's explicit request.

## Manual decks and English concept — 11 November 2026
- English concept delivered as Word and repository text; original German source retained. All nine Word pages rendered and inspected. Wireframes and flow diagrams are translated as English descriptions. Historical React/browser-storage proposal is explicitly superseded by Python/Streamlit/Supabase.
- 98 Python tests passed in 12.33s, including a full 15-card UI workflow. 13 isolated PostgreSQL-compatible checks passed: validation, atomicity, exact review matching, retry protection, RLS, denied writes, and exact content after a separate process restart.
- Browser walkthrough with fictional local data verified incomplete-card rejection, completing the last card, mandatory review and read-only publication. No fictional deck or student was added to production.
- Production migration applied successfully. Real account publication remains a user walkthrough; storage and permissions were tested in an isolated engine using the production migration.
- Changed feature files: app.py, logic.py, db.py, supabase/decks-schema.sql, tests/test_deck_rules.py, tests/test_deck_repository.py, tests/test_deck_ui.py, tests/decks_database.mjs, specs/third-feature.md, README.md and related concept/status documentation.

## Play — 11 November 2026
Implemented `specs/fourth-feature.md` with the user's one-hour search correction. Supabase stores private searches, invitations and rounds; matching and scoring are transactional. Play replaces its placeholder. New decks declare a profile-supported language; creators can fill missing legacy language once. Both deck languages and both players' languages must match.

Verification: 108 Python tests passed; 21 isolated PostgreSQL-compatible checks passed, including one-hour non-renewing queues, mismatches, invitation limits/cooldown, participant-only access, answer retries, 30-second expiry, all 30 questions, ratings, score privacy, XP/streak outcomes and progress across a fresh process. The existing deck fixture now declares English, as required by the new language rule. The former Play-placeholder expectation was replaced by actual lobby/round/navigation UI checks; existing other-tab expectations remain.

Browser preview used fictional users and verified the missing-course confirmation, one-hour search and cancellation. The production migration was applied successfully without creating synthetic accounts, invitations or duels. A two-real-account walkthrough is still needed for acceptance by the group. Expired matches settle on the next participant request, not a background job. Search eligibility is opt-in; no external invitation messages are sent automatically.

Changed application files: app.py, logic.py, db.py, supabase/play-schema.sql. Acceptance checks: tests/test_play.py, tests/test_play_ui.py, tests/play_database.mjs, updated tests/test_deck_rules.py and tests/test_navigation.py. Documentation: specs/fourth-feature.md, README.md, docs/product-brief.md, this status file.

## Play mode selection — 12 November 2026
Per the user's narrowed request, Play now shows Battle Mode and Study Mode buttons only; neither new ruleset is implemented yet. Clicking either shows its upcoming status. Study Mode is the next planned feature. The existing 30-question lobby remains available under Current 30-question duels, and active rounds and reviews keep their existing screens. No database migration or change to saved duels is part of this update.

The mode cards now use local vector book/sword artwork, indigo/mint gradients, and hover/focus animations. Keyboard focus triggers the same decoration; reduced-motion preferences disable movement. Buttons remain native Streamlit controls and both upcoming statuses are retained. No gameplay or data changes.
The same visual style extends to Decks, Play, Friends, Leaderboard, Study Plan and Profile with colour-inheriting vector icons and brief hover/focus animations. Labels remain visible, compact tablet layouts place icons above labels, and reduced-motion support also covers navigation.

## Dark mode — 12 November 2026
Added switchable native System/Light/Dark themes in the top-right app menu. Browser preference is managed by Streamlit, independently of authentication. Custom surfaces, brand text, mode cards, navigation, welcome screen, profile metrics, avatar editor and sharing controls adapt to the selected palette. Native inputs, dropdowns, dialogs and alerts inherit the configured theme. Captions use explicit readable colours without an additional opacity reduction. No database migration or gameplay changes.

Validation includes the existing application suite plus contrast checks for primary text, secondary text and links on both card palettes, native text on both configured backgrounds, and safe fallback for unknown appearance values. Manual browser checks cover switching, visible text, controls and restart persistence.
Custom colour tokens use CSS light-dark() with Streamlit's native color-scheme for immediate switching; the Python theme value is a fallback. Battle and Study icon circles use darker indigo/green backgrounds in dark mode. Browser checks confirmed both directions update immediately and that Dark remains selected after a full preview-process restart.
Avatar rendering now keeps the character on a transparent PNG backdrop, with a theme-aware circle in the header, profile and avatar editor. The avatar preview cache version was updated. Uploaded photos are not recoloured. Existing stored avatar images shown to friends gain the transparent backdrop when their owner next saves the profile; no stored photos or private data are rewritten automatically.

University lookup dark-mode fix: forms now retain Streamlit's native theme colours instead of applying custom light-dark() tokens inside a popover portal, which does not inherit the app's color-scheme. Rounded corners and spacing remain. Popover captions inherit native text colour. Search and profile persistence are unchanged.

## Study Mode — 12 November 2026
Implemented the approved specs/study-mode.md workflow in Streamlit and Supabase. New private editable Study decks support chapters and flexible question counts with mandatory review and revision conflict checks. Legacy published decks remain unchanged. Solo sessions combine chapter and progress filters, preserve answers and notes, and require explicit Next after feedback. Together sessions support accepted-friend invitations, mutual random queues and explicit open-session joins, matching course/language/size and (for random) university. Searches and matched rounds each have their own 24-hour deadline. Only completed players earn a permanent copy of their partner's full snapshot; future edits do not propagate. Results compare scores without XP/streak changes. Learning levels also receive future legacy duel answers via a database trigger. See docs/study-mode-verification.md for deployment, test commands, privacy boundaries and manual checks.

Study design refinement: Clicking Study Mode reveals Solo and Together inside the existing animated book card; choosing one opens its settings page. The settings reuse the original book artwork. Partner cards use the same high-resolution avatar renderer as profiles, with a question-mark badge for random partners and reduced-motion-aware hover effects. The progress legend uses small rounded colour swatches with adjacent names and counts, plus an info popover explaining the level rules. Incoming invitations appear above setup with course/language/size and separate accept/decline actions; new invites have their own settings. Course and language eligible friends are filtered through a permission-checked RPC, and the course requirement is enforced again on invitation and acceptance. Empty friend lists show an immediate Add friends hint. Existing installations apply supabase/study-design-update.sql; fresh installations use the updated study-schema.sql.

Study Together now explicitly explains N/2 questions from each deck and the shared question set. Learning-level preferences prioritize the contributor's half, with random no-repeat fallback when needed; preferences never affect matching. Existing installations apply supabase/study-level-preferences-update.sql. The Friends shortcut is labelled Go to Friends, with a Back to Study Together action on arrival. Verification: 11 targeted Python checks and 16 isolated database checks passed, including 15 new + 5 other questions for a 40-question session and matching users with different preferences.


Per-question calculator: both editors support an optional calculator flag; basic arithmetic popover is available only for enabled Study/Play questions. Apply `supabase/calculator-update.sql` to existing databases. Existing snapshots keep their permissions; legacy questions default off. No external calculator API.

The main Create New Deck entry now uses flexible Study decks with no fixed question count. Subsections can be selected or typed, and new questions inherit the current subsection. The original 15-question editor remains under Classic 30-question duels. Learning-level selectors use coloured markers in solo and together settings.
