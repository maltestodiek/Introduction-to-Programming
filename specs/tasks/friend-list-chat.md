# Start a chat from the friend list

Parent topic: [Social connections](../social-connections.md).

## Why

Accepted friends may already message each other, but a conversation could only be started from a Battle or Study partner menu or an existing thread. A student looking at their friend list had no direct way to write to a friend.

## What

On the Friends page, each entry under Your friends shows the friend's picture and their username as a button with a chat icon. Clicking it opens the private conversation with that friend, creating it if none exists yet, in the same chat view used elsewhere. Incoming and sent requests are not clickable, because only accepted friends may start a conversation. If the conversation cannot be opened, an error is shown and the Friends page stays as it was.

State and persistence: nothing new is stored. Opening uses the existing `chat_action` `open` operation, which enforces in Supabase that the two students are accepted friends or session partners.

## Out of scope

Changing who may chat, message rules, the Chats dropdown, friend requests, invitations, removal, or any database rule.

## Done when

1. Clicking a friend in Your friends opens the conversation with that friend.
2. Incoming and sent requests offer no chat button.
3. If opening fails, an error appears and no conversation opens.
4. Remove friend still works from the same entry.

Checks: `tests/test_friend_list_chat.py`, `tests/test_friends.py`, `tests/test_chat.py`, plus a manual check with a test friend.
