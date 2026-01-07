
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from httpx import Response
from app.db.models import Repository

@pytest.mark.asyncio
async def test_create_repository_success(async_client, mock_db_session):
    """Test creating a repository successfully."""
    
    # Needs to be a datetime for Pydantic/Model
    now = datetime.now()
    
    # Mock the GitHub service call
    # Also mock db.refresh to assign an ID to the repository object
    def assign_id(obj):
        obj.id = 1
    mock_db_session.refresh.side_effect = assign_id

    with patch("app.api.repositories.get_repository_data", new_callable=AsyncMock) as mock_get_data:
        mock_get_data.return_value = {
            "owner": "testowner",
            "repo_name": "testrepo",
            "full_name": "testowner/testrepo",
            "description": "Test Repo",
            "stars": 100,
            "forks": 50,
            "open_issues": 10,
            "primary_language": "Python",
            "html_url": "https://github.com/testowner/testrepo",
            "repo_created_at": now,
            "last_fetched_at": now,
        }
        
        response = await async_client.post(
            "/repositories",
            json={"repo_url": "https://github.com/testowner/testrepo"}
        )
        
        # Debug output if fails
        if response.status_code != 201:
            print(f"Response: {response.json()}")
            
        assert response.status_code == 201
        data = response.json()
        assert data["full_name"] == "testowner/testrepo"
        assert data["stars"] == 100
        
        # Verify DB interaction
        assert mock_db_session.add.called
        assert mock_db_session.commit.called

@pytest.mark.asyncio
async def test_create_repository_duplicate(async_client, mock_db_session):
    """Test creating a duplicate repository returns 409."""
    from sqlalchemy.exc import IntegrityError
    
    # We need a proper IntegrityError. The params are statement, params, orig
    mock_db_session.commit.side_effect = IntegrityError(None, None, Exception("Duplicate"))

    now = datetime.now()
    with patch("app.api.repositories.get_repository_data", new_callable=AsyncMock) as mock_get_data:
        mock_get_data.return_value = {
            "owner": "testowner",
            "repo_name": "testrepo",
            "full_name": "testowner/testrepo",
            "stars": 100,
            "forks": 50,
            "open_issues": 10,
            "html_url": "https://github.com/testowner/testrepo",
            "repo_created_at": now,
            "last_fetched_at": now,
        } 
        
        response = await async_client.post(
            "/repositories",
            json={"repo_url": "https://github.com/testowner/testrepo"}
        )
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_repository_success(async_client, mock_db_session):
    """Test retrieving a repository by ID."""
    
    now = datetime.now()
    mock_repo = Repository(
        id=1, 
        owner="testowner",
        repo_name="testrepo",
        full_name="testowner/testrepo", 
        stars=5,
        forks=2,
        open_issues=0,
        html_url="https://github.com/testowner/testrepo",
        repo_created_at=now,
        last_fetched_at=now,
        created_at=now,
        updated_at=now
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_repo
    mock_db_session.execute.return_value = mock_result

    response = await async_client.get("/repositories/1")
    
    assert response.status_code == 200
    assert response.json()["full_name"] == "testowner/testrepo"

@pytest.mark.asyncio
async def test_get_repository_not_found(async_client, mock_db_session):
    """Test retrieving a non-existent repository."""
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    response = await async_client.get("/repositories/999")
    
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_repository(async_client, mock_db_session):
    """Test deleting a repository."""
    
    now = datetime.now()
    mock_repo = Repository(
        id=1, 
        owner="testowner",
        repo_name="testrepo",
        full_name="testowner/testrepo", 
        stars=5,
        forks=2,
        open_issues=0,
        html_url="https://github.com/testowner/testrepo",
        repo_created_at=now,
        last_fetched_at=now,
        created_at=now,
        updated_at=now
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_repo
    mock_db_session.execute.return_value = mock_result

    response = await async_client.delete("/repositories/1")
    
    assert response.status_code == 204
    
    assert mock_db_session.execute.call_count >= 2
    assert mock_db_session.commit.called
