from app.database import DATABASE_URL, AsyncSessionLocal


def test_database_url_is_configured():
    assert DATABASE_URL
    assert "postgresql" in DATABASE_URL or "sqlite" in DATABASE_URL


def test_async_session_factory_exists():
    assert AsyncSessionLocal is not None
