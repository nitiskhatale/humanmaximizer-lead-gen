"""
Shared pytest fixtures.

DATABASE_URL is overridden to in-memory SQLite so tests never touch the
production/dev database. The schema is created fresh for every test session.
"""
import os

# Override before any app modules are imported so Settings picks it up.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from main import app
from models import init_db


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Create all tables once for the whole test session."""
    await init_db()


@pytest_asyncio.fixture
async def client(setup_db):
    """Async HTTPX client wired to the FastAPI app (no real network)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
