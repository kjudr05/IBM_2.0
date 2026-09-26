"""
Pytest configuration for the backend test suite.

Provides:
  - db_override fixture: patches the database module to use an in-memory
    SQLite database for each test function, so tests are fully isolated and
    never touch the real data/ directory.
  - test_client fixture: an httpx AsyncClient wired to the FastAPI app with
    the in-memory DB active.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import app.db.database as db_module
from app.db.database import _SCHEMA_SQL
from app.main import create_app


@pytest_asyncio.fixture(autouse=True)
async def db_override():
    """
    Replace the shared DB connection with a fresh in-memory SQLite database
    for each test.  Runs automatically for every test in the suite.
    """
    import aiosqlite

    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.executescript(_SCHEMA_SQL)
    await conn.commit()

    # Patch module-level connection
    original = db_module._connection
    db_module._connection = conn

    yield conn

    db_module._connection = original
    await conn.close()


@pytest_asyncio.fixture
async def test_client(db_override):
    """AsyncClient pointed at the FastAPI app with the in-memory DB active."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
