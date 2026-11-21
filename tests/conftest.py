"""UI tests use dummy configuration, never local account credentials."""
import pytest

@pytest.fixture(autouse=True)
def isolated_app_configuration(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL','https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY','sb_publishable_test_only')
    monkeypatch.setenv('APP_URL','http://localhost:8501')
    monkeypatch.setenv('LEADERBOARD_DEMO','0')  # a developer's local preview switch must not leak into tests

@pytest.fixture(autouse=True)
def isolated_browser_storage(monkeypatch):
    monkeypatch.setattr('launch.browser_bridge',lambda *a,**k:{})


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    """Require fake service responses, even when application code catches a network error."""
    import socket

    attempts = []

    def block(*args, **kwargs):
        attempts.append(True)
        raise AssertionError('Use a fake response instead of a network connection in tests.')

    def guard_connect(original):
        def connect(sock, *args, **kwargs):
            if sock.family in (socket.AF_INET, socket.AF_INET6):
                block()
            return original(sock, *args, **kwargs)
        return connect

    monkeypatch.setattr(socket, 'getaddrinfo', block)
    for name in ('connect', 'connect_ex'):
        monkeypatch.setattr(socket.socket, name, guard_connect(getattr(socket.socket, name)))
    yield
    assert not attempts, 'A test tried to reach a network service. Supply a fake response.'
