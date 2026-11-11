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
