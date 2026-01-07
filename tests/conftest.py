
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.sessions import get_db
from app.db.base import Base

# Use an in-memory SQLite database for testing, or a separate Postgres test DB
# Since the app uses asyncpg, we need an async driver. 
# For simplicity in this assessment context without spinning up a fresh PG container,
# we will mock the database session or use a lightweight approach.
# HOWEVER, the best practice is to use a real DB or sqlite+aiosqlite.
# Given the user has 'postgresql+asyncpg' in requirements, let's try to mock the session 
# or use a different database URL for testing if possible.
#
# BUT: To keep it robust and simple without requiring extra install (aiosqlite),
# we will use `unittest.mock` for the repository layer in some tests, 
# OR use the dependency override technique with a mocked session.
#
# Let's go with Dependency Override + Mocked Session for unit/integration split.
# Actually, strict integration tests should hit a DB. 
# Let's assume the user has a test DB or we can mock the `execute` calls.
#
# Let's use a Mocked AsyncSession for maximum portability without external DB deps.

from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_db_session():
    """Fixture that returns a mock AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    # Default behavior for commit/rollback
    session.commit.return_value = None
    session.rollback.return_value = None
    session.refresh.return_value = None
    return session

@pytest.fixture
def client(mock_db_session) -> Generator[TestClient, None, None]:
    """Fixture for FastAPI TestClient with DB override."""
    
    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def async_client(mock_db_session) -> AsyncGenerator[AsyncClient, None]:
    """Fixture for httpx AsyncClient with DB override."""
    
    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db
    
    # Use ASGITransport for direct app testing without binding to a port
    transport = ASGITransport(app=app)
    
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()
