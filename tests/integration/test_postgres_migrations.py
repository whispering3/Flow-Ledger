import os

import pytest
from sqlalchemy import create_engine, inspect

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("FLOWLEDGER_RUN_INTEGRATION") != "1",
    reason="Set FLOWLEDGER_RUN_INTEGRATION=1 with a disposable PostgreSQL database",
)
def test_migrations_create_the_required_postgres_schema() -> None:
    database_url = os.environ["FLOWLEDGER_DATABASE_URL"]
    engine = create_engine(database_url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert {
        "organizations",
        "projects",
        "api_keys",
        "events",
        "outbox_messages",
        "destinations",
        "executions",
        "execution_attempts",
    } <= tables
