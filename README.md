# GitHub Repository Insights Service

A robust REST API service built with **FastAPI** and **PostgreSQL** that acts as a bridge between a local database and the **GitHub API**. This service allows users to save, query, refresh, and delete GitHub repository metadata while demonstrating complex data flows, strict validation, and comprehensive testing.

---

## Table of Contents

1. [Problem Understanding & Assumptions](#1-problem-understanding--assumptions)
2. [Design Decisions](#2-design-decisions)
3. [Solution Approach](#3-solution-approach)
4. [Error Handling Strategy](#4-error-handling-strategy)
5. [How to Run the Project](#5-how-to-run-the-project)
6. [API Documentation](#6-api-documentation)
7. [Testing](#7-testing)

---

## 1. Problem Understanding & Assumptions

### Interpretation

The core requirement is to build a REST API service that:
- Implements exactly **four CRUD endpoints** (POST, GET, PUT, DELETE)
- Integrates with an **external API** (GitHub) for data enrichment
- Persists all data to a **PostgreSQL database**
- Enforces **strict validation** using Pydantic models
- Returns appropriate **HTTP status codes**

### Use Case: GitHub Repository Insights Service

I chose to build a **GitHub Repository Insights Service** that allows users to:
1. **Add** a GitHub repository by providing its URL — the service fetches metadata from GitHub and stores it locally
2. **Retrieve** stored repository information by ID
3. **Refresh** repository data with the latest information from GitHub
4. **Delete** repositories from the local database

This use case demonstrates meaningful external API integration where the POST and PUT endpoints fetch real-time data from GitHub before persisting to the database.

### Assumptions

| Area | Assumption |
|------|------------|
| **Authentication** | No user authentication is required; the API is publicly accessible. GitHub API access uses an optional personal access token for higher rate limits. |
| **Data Format** | Only GitHub repository URLs in the format `https://github.com/{owner}/{repo}` are supported. Other Git hosting services (GitLab, Bitbucket) are explicitly rejected. |
| **External API Reliability** | GitHub API may be temporarily unavailable. The service handles timeouts (configurable, default 10s) and returns appropriate 503/502 errors. |
| **Rate Limits** | The service does not implement internal rate limiting. GitHub's rate limits (60 requests/hour unauthenticated, 5000/hour with token) are handled via optional token configuration. |
| **Data Freshness** | Repository metadata is fetched at creation time and only refreshed via explicit PUT request. There is no background sync. |
| **Duplicate Handling** | Duplicate repositories (same `owner/repo`) are rejected with 409 Conflict. Uniqueness is enforced at the database level. |

---

## 2. Design Decisions

### Database Schema

The `repositories` table stores GitHub repository metadata with the following structure:

```sql
CREATE TABLE repositories (
    id SERIAL PRIMARY KEY,
    owner VARCHAR(255) NOT NULL,
    repo_name VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL UNIQUE,  -- Indexed for fast lookups
    description TEXT,
    stars INTEGER NOT NULL,
    forks INTEGER NOT NULL,
    open_issues INTEGER NOT NULL,
    primary_language VARCHAR(255),
    html_url VARCHAR(255) NOT NULL,
    repo_created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_fetched_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX ix_repositories_full_name ON repositories(full_name);
```

**Indexing Strategy:**
- `full_name` is indexed and unique — enables O(1) duplicate detection and fast lookups
- `id` is the primary key — used for all CRUD operations after creation

**Design Rationale:**
- `last_fetched_at` tracks data freshness for potential stale-data logic
- `created_at` / `updated_at` timestamps support auditing
- `owner` and `repo_name` are stored separately for potential future filtering

### Project Structure

```
app/
├── api/                    # API layer (Controllers)
│   ├── __init__.py
│   └── repositories.py     # All 4 CRUD endpoints
├── core/                   # Configuration
│   └── config.py           # Pydantic Settings with .env support
├── db/                     # Database layer
│   ├── base.py             # SQLAlchemy Base class
│   ├── models.py           # ORM models (Repository)
│   └── sessions.py         # Async session factory
├── schemas/                # Pydantic schemas (DTOs)
│   └── repository.py       # Request/Response models
├── services/               # Business logic layer
│   └── github_service.py   # GitHub API integration
└── main.py                 # FastAPI application factory
tests/
├── unit/                   # Unit tests
│   └── test_github_service.py
└── integration/            # Integration tests
    └── rest_repositories_api.py
```

**Architecture Pattern: Layered Architecture**
- **API Layer**: Handles HTTP concerns, routing, dependency injection
- **Service Layer**: Contains business logic, external API calls
- **Data Layer**: Database models, session management
- **Schema Layer**: Pydantic models for validation and serialization

This separation ensures:
- Easy testing (services can be tested without HTTP layer)
- Clear boundaries between concerns
- Reusable business logic

### Validation Logic

Beyond basic type checking, the following validations are enforced:

| Validation | Implementation |
|------------|----------------|
| **Valid GitHub URL** | `HttpUrl` Pydantic type ensures proper URL format |
| **GitHub domain only** | Custom `parse_github_repo_url()` rejects non-GitHub URLs |
| **Valid path format** | URL must contain `/{owner}/{repo}` path structure |
| **Repository existence** | GitHub API 404 is translated to user-friendly error |
| **Duplicate prevention** | Database UNIQUE constraint with IntegrityError handling |

**Example Schema with Validation:**

```python
class RepositoryCreateRequest(BaseModel):
    repo_url: Annotated[HttpUrl, AfterValidator(url_to_str)] = Field(
        ...,
        description="GitHub repository URL",
        examples=["https://github.com/owner/repo"]
    )
```

### External API Design

**GitHub API Integration:**

| Aspect | Implementation |
|--------|----------------|
| **Base URL** | Configurable via `GITHUB_API_BASE_URL` (default: `https://api.github.com`) |
| **Authentication** | Optional Bearer token via `GITHUB_TOKEN` environment variable |
| **Timeout** | Configurable via `GITHUB_TIMEOUT_SECONDS` (default: 10s) |
| **HTTP Client** | `httpx.AsyncClient` for async, connection-pooled requests |

**Request Flow:**
```
User Request → Parse URL → Fetch from GitHub API → Map Response → Save to DB
```

---

## 3. Solution Approach

### Data Flow Walkthrough

#### POST /repositories (Create)

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant GitHubService
    participant GitHub
    participant Database

    Client->>API: POST /repositories {repo_url}
    API->>API: Validate Pydantic schema
    API->>GitHubService: get_repository_data(repo_url)
    GitHubService->>GitHubService: parse_github_repo_url()
    GitHubService->>GitHub: GET /repos/{owner}/{repo}
    GitHub-->>GitHubService: Repository JSON
    GitHubService->>GitHubService: map_github_response()
    GitHubService-->>API: Mapped data dict
    API->>Database: INSERT repository
    Database-->>API: New repository record
    API-->>Client: 201 Created + repository JSON
```

#### GET /repositories/{id} (Read)

```
Client → API → Database Query → Return 200 OK or 404 Not Found
```

#### PUT /repositories/{id} (Refresh)

```
Client → API → Fetch existing from DB → Fetch fresh data from GitHub → Update DB → Return 200 OK
```

#### DELETE /repositories/{id} (Delete)

```
Client → API → Check exists in DB → DELETE → Return 204 No Content or 404 Not Found
```

---

## 4. Error Handling Strategy

### HTTP Status Codes

| Status Code | Condition |
|-------------|-----------|
| `200 OK` | Successful GET or PUT |
| `201 Created` | Repository successfully created |
| `204 No Content` | Repository successfully deleted |
| `404 Not Found` | Repository ID not in database OR GitHub repo doesn't exist |
| `409 Conflict` | Attempting to add duplicate repository |
| `422 Unprocessable Entity` | Invalid URL format or non-GitHub URL |
| `502 Bad Gateway` | GitHub API returned an error (4xx/5xx) |
| `503 Service Unavailable` | Cannot connect to GitHub API (network error, timeout) |

### Error Handling Implementation

**1. External API Failures:**

```python
async def fetch_repository_from_github(owner: str, repo: str) -> dict:
    try:
        response = await client.get(url, headers=headers)
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to GitHub API: {str(e)}",
        )

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Repository not found on GitHub")

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="GitHub API error")
```

**2. Database Failures:**

```python
try:
    await db.commit()
except IntegrityError:
    await db.rollback()
    raise HTTPException(status_code=409, detail="Repository already exists")
```

**3. Validation Failures:**

Pydantic automatically returns 422 with detailed error messages for invalid request bodies.

### Future Enhancements

For production, consider adding:
- Global exception handler middleware for unexpected errors
- Structured logging for error tracking
- Circuit breaker pattern for GitHub API resilience
- Retry logic with exponential backoff

---

## 5. How to Run the Project

### Prerequisites

- Python 3.10+
- PostgreSQL 13+
- pip or poetry

### Setup Instructions

**1. Clone the repository:**

```bash
git clone https://github.com/your-username/showbay.git
cd showbay
```

**2. Create a virtual environment:**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

**3. Install dependencies:**

```bash
pip install fastapi uvicorn sqlalchemy asyncpg pydantic pydantic-settings httpx pytest pytest-asyncio httpx
```

**4. Configure environment variables:**

Create a `.env` file in the project root:

```env
# Required
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/showbay_db

# Optional (for higher GitHub API rate limits)
GITHUB_TOKEN=ghp_your_personal_access_token

# Optional (defaults shown)
GITHUB_API_BASE_URL=https://api.github.com
GITHUB_TIMEOUT_SECONDS=10
```

**5. Create the database:**

```bash
# Connect to PostgreSQL and create the database
psql -U postgres -c "CREATE DATABASE showbay_db;"
```

**6. Run the application:**

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string (asyncpg format) |
| `GITHUB_TOKEN` | No | `None` | GitHub personal access token for API auth |
| `GITHUB_API_BASE_URL` | No | `https://api.github.com` | GitHub API base URL |
| `GITHUB_TIMEOUT_SECONDS` | No | `10` | Timeout for GitHub API requests |

---

## 6. API Documentation

### Interactive Documentation

Once running, access the interactive API docs at:
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

### Endpoints

#### POST /repositories

Create a new repository by fetching data from GitHub.

**Request:**
```bash
curl -X POST "http://127.0.0.1:8000/repositories" \
     -H "Content-Type: application/json" \
     -d '{"repo_url": "https://github.com/fastapi/fastapi"}'
```

**Response (201 Created):**
```json
{
  "id": 1,
  "full_name": "fastapi/fastapi",
  "description": "FastAPI framework, high performance, easy to learn...",
  "stars": 75000,
  "forks": 6300,
  "open_issues": 500,
  "primary_language": "Python",
  "html_url": "https://github.com/fastapi/fastapi",
  "repo_created_at": "2018-12-08T00:00:00Z",
  "last_fetched_at": "2026-01-08T00:00:00Z"
}
```

---

#### GET /repositories/{repository_id}

Retrieve a stored repository by ID.

**Request:**
```bash
curl "http://127.0.0.1:8000/repositories/1"
```

**Response (200 OK):**
```json
{
  "id": 1,
  "full_name": "fastapi/fastapi",
  "description": "FastAPI framework...",
  ...
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Repository not found"
}
```

---

#### PUT /repositories/{repository_id}

Refresh repository data from GitHub.

**Request:**
```bash
curl -X PUT "http://127.0.0.1:8000/repositories/1"
```

**Response (200 OK):**
```json
{
  "id": 1,
  "full_name": "fastapi/fastapi",
  "stars": 75500,  // Updated value
  ...
}
```

---

#### DELETE /repositories/{repository_id}

Delete a repository from the database.

**Request:**
```bash
curl -X DELETE "http://127.0.0.1:8000/repositories/1"
```

**Response:** `204 No Content`

---

## 7. Testing

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run only unit tests
python -m pytest tests/unit/

# Run only integration tests
python -m pytest tests/integration/

# Run with coverage
python -m pytest --cov=app
```

### Test Structure

**Unit Tests** (`tests/unit/`):
- Test individual logic components in isolation
- Example: `test_github_service.py` tests URL parsing logic

**Integration Tests** (`tests/integration/`):
- Test API endpoints with mocked dependencies
- Use HTTPX AsyncClient for async testing

### Current Test Coverage

| Test | Description |
|------|-------------|
| `test_parse_valid_github_url` | Validates correct parsing of GitHub URLs |
| `test_parse_invalid_domain` | Ensures non-GitHub URLs are rejected |
| `test_parse_invalid_path` | Ensures malformed URLs are rejected |

### Testing Philosophy

- **Mock external APIs**: GitHub API calls are mocked to ensure test reliability
- **Isolated database**: Integration tests use a separate test database or in-memory SQLite
- **Fast feedback**: Unit tests run without network or database dependencies

---

## License

MIT License

---

## Author

Built as a take-home assessment demonstrating Python backend engineering skills with FastAPI, PostgreSQL, and external API integration.
