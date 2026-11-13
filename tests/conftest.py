"""UI tests use dummy configuration, never local account credentials."""
import pytest

@pytest.fixture(autouse=True)
def isolated_app_configuration(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL','https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY','sb_publishable_test_only')
    monkeypatch.setenv('APP_URL','http://localhost:8501')

@pytest.fixture(autouse=True)
def isolated_browser_storage(monkeypatch):
    monkeypatch.setattr('launch.browser_bridge',lambda *a,**k:{})
