# Second feature: friend invitations

## Why
Students need to find and connect with real classmates before asynchronous duels can be implemented. This replaces the earlier simulated-only/friends-later delivery sequence for this workflow.

## What
Use the existing Python, Streamlit, uv, pytest and Supabase stack. Supabase stores friend codes, pending requests, invitation tokens and accepted friendships against verified Auth user IDs. No credentials are encoded in codes or links.

Each profile gets a random, unique eight-character uppercase alphanumeric friend code, displayed with a leading #. Exclude confusing characters (0/O and 1/I). Normalize input case and optional #. Generate codes on the server with a unique constraint and retry collisions; keep the code stable across sessions and profile edits. The code is an identifier, never a login credential.

Profile -> Friends shows My code, Add friend, Invite a friend, Incoming requests, Sent requests, and Friends. Entering a valid code previews the student's public username and active image. Send request creates a pending request. Only the recipient can accept or decline; the sender can cancel a pending request. Acceptance creates one mutual friendship; either friend can remove it. No emails or private study information appear in lookup results.

Proposed link behavior for group review: an invitation uses a separate random, unguessable token, valid seven days and revocable by the sender. Opening a link does not create a friendship. After signing in or completing signup/profile setup, the recipient sees the sender and clicks Accept invitation. This records mutual consent without requiring the sender to approve a second time. The reusable link can invite multiple friends until expiration or revocation. Only a digest of the token is stored. Preserve invitation context through signup/login; expired or revoked links cannot be accepted.

Sharing offers Copy link, WhatsApp, Email and Share. Native Share uses the device share sheet when available; installed apps and browser support determine whether Messenger or other targets appear. Copy link remains available as a fallback. WhatsApp/email open a composed message for the user to send; the app never sends messages automatically and needs no messaging-provider credentials. A deployed public HTTPS app URL is required for links that work on friends' devices. Never present localhost links as externally usable invitations.

Supabase enforces participant-only access to requests and friendships. Only the authenticated user can initiate actions as themselves. Use database transactions and uniqueness constraints to prevent duplicate/crossed requests and duplicate friendships. Exact-code lookup only; no public listing of codes. Bound request creation and code-lookup attempts to reduce guessing/spam. Do not broaden private profile access.

## State and persistence
- Friend code: user ID, code, creation time; unique code and one per user.
- Request: sender ID, recipient ID, status, timestamps; one active relationship per unordered pair.
- Friendship: two distinct user IDs, acceptance timestamp; unique unordered pair.
- Invitation: owner ID, token digest, expiry, revocation; acceptance associates authenticated recipient.
- Pending invitation navigation: browser/session context only until explicitly accepted; never authenticate from an invitation.
All accepted changes persist in Supabase after a full app restart. Rejected actions leave stored state unchanged.

## File and test proposal
- app.py: Friends navigation, code lookup, requests and accept/decline controls.
- logic.py: code normalization and share-link validation.
- db.py: authenticated friendship repository operations.
- sharing.py: native sharing widget and share URLs.
- supabase/friends-schema.sql: tables, uniqueness, RPC transactions, permissions and row-level policies.
- tests/test_friends_logic.py: code formats and safe share URLs.
- tests/test_friends_repository.py: permitted actions, rejected actions, provider failures.
- tests/test_friends_ui.py: invitation preservation through auth, UI states and share fallback.
- tests/sql/friends_acceptance.sql: transactional two-user and third-user permissions checks against a test environment.

## Out of scope
Duels, live gameplay, chat, matching, notifications outside the app, contact imports, automatic WhatsApp/email delivery, and deployment itself. Deployment requires a separate concrete hosting decision; local testing can use independent sessions on the same computer.

## Done when / expected tests for group review
1. Two users receive distinct stable codes; a simulated collision retries without assigning a duplicate.
2. Valid code -> matching public profile -> pending request. Recipient accepts -> both see exactly one friendship, including after restarting the app.
3. Invalid/unknown codes, self requests, duplicates and requests to existing friends are rejected without writes. Crossed requests do not auto-accept or duplicate.
4. A recipient may decline; a sender may cancel. A third user cannot read or alter either request; a sender cannot accept their own request.
5. A signed-out visitor can open a valid invitation, finish login/profile setup, then explicitly accept it. Opening the URL alone writes no friendship.
6. Expired, revoked, malformed and self-invitation links fail without writes. Repeated acceptance is idempotent.
7. Removing a friendship removes it from both lists. Simultaneous acceptance/removal cannot corrupt the relationship.
8. Copy, WhatsApp and email contain the configured public invitation URL. Native sharing failure/cancellation preserves the invitation and offers a fallback. No message is sent by tests.
9. Anonymous callers cannot enumerate codes, requests or friendships. Friend actions cannot expose emails, courses, degree, field of study or inactive images.
10. A failed network response does not falsely display success; refreshing reads the authoritative relationship from Supabase.

Review these outcomes with the group before writing implementation. Existing authentication/profile acceptance checks remain unchanged.
