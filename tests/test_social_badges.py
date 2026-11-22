from test_deck_ui import button, deck_app


def badge(at, destination, count):
    content = f'"{count}"' if count else 'none'
    rule = f'.st-key-open_{destination}{{--social-count:{content}}}'
    assert any(rule in element.proto.body for element in at.get('html'))
    assert not at.exception


def test_opening_one_chat_only_clears_that_conversations_messages(monkeypatch):
    unread = {'Alex': 2, 'Noor': 1}

    def chat(repo, action, data=None):
        if action == 'list':
            return {'threads': [
                {'id': name, 'username': name, 'preview': 'Hello', 'unread': count}
                for name, count in unread.items()
            ]}
        name = data['id']
        if action == 'read':
            return {'partner': {'id': name, 'username': name}, 'has_older': False,
                    'messages': [{'id': 3, 'from_me': False, 'body': 'Hello', 'created_at': '2026-11-22T10:00:00'}]}
        assert action == 'seen'
        unread[name] = 0
        return {}

    monkeypatch.setattr('db.ChatRepository.action', chat)
    at = deck_app(monkeypatch)
    badge(at, 'chats', 3)
    button(at, 'Chats').click().run()
    badge(at, 'chats', 3)
    button(at, 'Open chat with Alex (2 unread)').click().run()
    badge(at, 'chats', 1)
    button(at, 'Open chat with Noor (1 unread)').click().run()
    badge(at, 'chats', 0)


def test_friend_badge_survives_view_and_only_drops_after_resolution(monkeypatch):
    incoming = [{'id': name, 'person': {'id': name, 'username': name}} for name in ('Alex', 'Noor')]
    sent = [{'id': 'sam', 'person': {'username': 'Sam'}}]

    def friends(repo, action, value=''):
        if action == 'list':
            return {'code': 'AB23CD45', 'incoming': incoming, 'sent': sent, 'friends': []}
        assert action in ('accept', 'decline')
        incoming.remove(next(item for item in incoming if item['id'] == value))
        return {'message': 'Saved'}

    monkeypatch.setattr('db.FriendsRepository.action', friends)
    monkeypatch.setattr('db.FriendsRepository.incoming_count', lambda self, user: len(incoming))
    monkeypatch.setattr('db.FriendsRepository.university_profiles', lambda self: {'profiles': []})
    at = deck_app(monkeypatch)
    badge(at, 'friends', 2)
    button(at, 'Friends').click().run()
    badge(at, 'friends', 2)
    invitations = next(block for block in at.get('flex_container')
                       if any('>Open invitations</h2>' in item.proto.body for item in block.get('html'))
                       and block.proto.id.endswith('-friends_open_invitations'))
    assert {item.key for item in invitations.button} >= {'accept_Alex', 'decline_Noor', 'cancel_sam'}
    assert {item.value for item in invitations.markdown} >= {'**Received**', '**Sent**'}
    assert all(item.value != 'No pending requests.' for item in invitations.caption)
    at.button(key='accept_Alex').click().run()
    badge(at, 'friends', 1)
    at.button(key='decline_Noor').click().run()
    badge(at, 'friends', 0)
