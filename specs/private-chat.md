# Private one-to-one chat

## Why
Matched Battle and Study partners need a private way to discuss their session.

## What
Use the existing Supabase authenticated API and database. Add a Chats dropdown beside Profile with partner image, username, last-message preview and unread count. Open a conversation from a matched partner or the dropdown. Store messages across reloads; refresh open chats every three seconds with Streamlit fragments. This first release uses polling, not a new external chat service.

Only accepted friends or actual Battle/paired Study participants may start a conversation. Once created, only its two participants may list, read or send messages. Pending random searches do not grant access. Keep email, private profile fields and raw avatar settings out of chat responses. Limit messages to 2,000 characters, reject blank messages, rate-limit sends and use client request IDs to make retries safe. Messages are plain text. Loading older history must not lose new messages or incorrectly mark unseen messages read.

## Out of scope
Group chat, attachments, calls, typing indicators, read receipts, and push/email notifications.

## Done when
Two eligible users can exchange messages and resume after a restart; an unrelated third user and anonymous callers cannot access the conversation. Retries do not duplicate messages. Empty/oversized messages do not write data. Unread counts are per recipient. The dropdown shows name, image and preview; clicking a matched partner opens the correct private chat. A clearly labelled dummy conversation demonstrates the feature without contacting real users.

## Session history and friendship extension
Play shows ongoing sessions followed by historical Battle and Study sessions, including completed and expired Study sessions. Solo sessions have no partner menu. Both ongoing and historical matched participants offer Send message and Send friend request. A request uses the existing pending/acceptance flow and rate limit; it never automatically creates an accepted friendship. Unrelated users cannot request friendship by guessing an ID through this shortcut.
