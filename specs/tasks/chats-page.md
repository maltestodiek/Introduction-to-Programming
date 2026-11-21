# Chats page

Parent topic: [Social connections](../social-connections.md).

## Why

Chats is a sidebar destination. The inbox and the open conversation need room to be visible together.

## What

Open Chats from the sidebar. Use the available width and height of the page. On desktop, show the conversation list on the left and the wider conversation on the right. On narrow screens, give the inbox or open chat the full width and show Back to inbox in an open chat. Show the participant's image, name, latest message preview and any unread count. The inbox updates every 15 seconds and the open conversation every three seconds.

Start conversation replaces the inbox list with accepted friends who have no existing thread. Selecting a friend opens their private chat. Existing Chats, Friends and session links open the same conversation view. Keep the unread total available on the sidebar when visiting other pages.

The current page uses the existing navigation restore rules. The active thread, friend picker and drafts are held in the app session. Supabase remains the source of truth for accepted friendships, private threads, history and unread counts.

## Out of scope

Message authorization, delivery rules, retention, database migrations, group conversations and attachments.

## Done when

1. Chats opens the page. Selecting a conversation opens it beside the list without a modal.
2. Start conversation offers only accepted friends without a thread. Selecting a friend opens their thread without sending a message.
3. A rejected open leaves the picker and selection available. A rejected send retains the draft and retries use the same request ID.
4. Friends and matched partner shortcuts still open the right thread. Sending messages, friendship controls and unread updates use the existing rules.
5. A verified returning browser can reopen Chats, where saved conversations can be selected again. The panes work in light and dark modes and on narrow windows.
6. Only the conversation and friend lists and the message history scroll. The page heading, controls and message composer fit in the window.

Checks: tests/test_chat.py, tests/test_friend_list_chat.py, tests/test_friends_header.py, and the local Chats page.
