from backend.config import Settings


def test_cloud_postgres_url_uses_psycopg3_driver() -> None:
    settings = Settings(DATABASE_URL="postgresql://user:password@host/database")

    assert settings.sqlalchemy_database_url == (
        "postgresql+psycopg://user:password@host/database"
    )


def test_explicit_driver_and_sqlite_urls_are_preserved() -> None:
    postgres = Settings(DATABASE_URL="postgresql+psycopg://user:password@host/database")
    sqlite = Settings(DATABASE_URL="sqlite:///local.db")

    assert postgres.sqlalchemy_database_url == postgres.database_url
    assert sqlite.sqlalchemy_database_url == sqlite.database_url
