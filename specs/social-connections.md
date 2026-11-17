# Social connections — friends, invitations and private chat

## Why
Help students connect with classmates and continue conversations with study partners.

## What
### Friends and invitations
Use the existing Python, Streamlit, uv, pytest and Supabase stack. Supabase stores friend codes, pending requests, invitation tokens and accepted friendships against verified Auth user IDs. No credentials are encoded in codes or links.

Each profile gets a random, unique eight-character uppercase alphanumeric friend code, displayed with a leading #. Exclude confusing characters (0/O and 1/I). Normalize input case and optional #. Generate codes on the server with a unique constraint and retry collisions; keep the code stable across sessions and profile edits. The code is an identifier, never a login credential.

Profile -> Friends shows My code, Add friend, Invite a friend, Incoming requests, Sent requests, and Friends. Entering a valid code previews the student's public username and active image. Send request creates a pending request. Only the recipient can accept or decline; the sender can cancel a pending request. Acceptance creates one mutual friendship; either friend can remove it. No emails or private study information appear in lookup results.

Approved link behavior: an invitation uses a separate random, unguessable token, valid seven days and revocable by the sender. Opening a link does not create a friendship. After signing in or completing signup/profile setup, the recipient sees the sender and clicks Accept invitation. This records mutual consent without requiring the sender to approve a second time. The reusable link can invite multiple friends until expiration or revocation. Only a digest of the token is stored. Preserve invitation context through signup/login; expired or revoked links cannot be accepted.

Sharing offers Copy link, WhatsApp, Email and Share. Native Share uses the device share sheet when available; installed apps and browser support determine whether Messenger or other targets appear. Copy link remains available as a fallback. WhatsApp/email open a composed message for the user to send; the app never sends messages automatically and needs no messaging-provider credentials. A deployed public HTTPS app URL is required for links that work on friends' devices. Never present localhost links as externally usable invitations.

Supabase enforces participant-only access to requests and friendships. Only the authenticated user can initiate actions as themselves. Use database transactions and uniqueness constraints to prevent duplicate/crossed requests and duplicate friendships. Exact-code lookup only; no public listing of codes. Bound request creation and code-lookup attempts to reduce guessing/spam. Do not broaden private profile access.


### Private chat
Use the existing Supabase authenticated API and database. Add a Chats dropdown beside Profile with partner image, username, last-message preview and unread count. Open a conversation from a matched partner or the dropdown. Store messages across reloads; refresh open chats every three seconds with Streamlit fragments. This first release uses polling, not a new external chat service.

Only accepted friends or actual Battle/paired Study participants may start a conversation. Once created, only its two participants may list, read or send messages. Pending random searches do not grant access. Keep email, private profile fields and raw avatar settings out of chat responses. Limit messages to 2,000 characters, reject blank messages, rate-limit sends and use client request IDs to make retries safe. Messages are plain text. Loading older history must not lose new messages or incorrectly mark unseen messages read.


Open a participant's name menu in either ongoing or historical Battle/Study sessions to send a friend request or message. The chat header also offers Send friend request, Friend request sent, Accept friend request or Friends according to the current relationship. A conversation permits a request, not automatic friendship. Only the recipient can accept it; retain the shared request rate limit and duplicate protection.

Chat fits on screen with only message history scrolling. Show both participants' actual profile pictures beside messages. Opening a conversation closes the inbox dropdown; failed sends retain their draft. Supabase persists all accepted friendship and chat changes across restarts. Browser/session state holds unsent text only.

## Out of scope
Group chats, attachments, calls, typing indicators, push/email notifications, contact imports and automatically sending external sharing messages.

## Done when
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

The user approved these outcomes and implementation on 11 November 2026. Existing authentication/profile acceptance checks remain unchanged.

Rate-limit bookkeeping may record rejected attempts; rejected actions never change profiles, invitations or relationships. The Friends count and list are private to the current account.

Private conversations reject third-party and anonymous reads/writes. Message retries do not duplicate content; blank/oversized messages do not write data. Unread counts and read cursors are per recipient. Chats reopen with saved history after a process restart. Existing chat participants and actual matched session partners can request friendship; guessing an unrelated user ID cannot bypass eligibility. Pending requests never auto-accept.

Checks: `tests/test_friends.py`, `tests/test_chat.py`, `tests/chat_database.mjs`, `tests/session_friends_database.mjs`, and `tests/sql/friends_*.sql` in an isolated test environment.
