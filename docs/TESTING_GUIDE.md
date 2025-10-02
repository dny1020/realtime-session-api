# Testing Guide

This guide covers testing strategies and best practices for the Contact Center API.

## Test Structure

```
tests/
├── test_auth.py          # Authentication and JWT tests
├── test_interaction.py   # API endpoint tests
├── test_asterisk.py      # Asterisk service tests
├── conftest.py           # Pytest fixtures (to be created)
└── README.md            # Testing documentation
```

## Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_auth.py

# Run specific test
pytest tests/test_auth.py::test_password_hash_and_token_flow

# Run with verbose output
pytest -v

# Run with debug output
pytest -s
```

## Test Configuration

### Environment Variables for Testing

Create a `.env.test` file:

```bash
# Database
DISABLE_DB=true  # Use in-memory mode for tests
DATABASE_URL=postgresql://test_user:test_pass@localhost:5432/test_db

# Asterisk (mock in tests)
ARI_HTTP_URL=http://localhost:8088/ari
ARI_USERNAME=test_user
ARI_PASSWORD=test_pass

# Security
SECRET_KEY=test_secret_key_not_for_production
DEBUG=true
DOCS_ENABLED=true

# Metrics
METRICS_ENABLED=false  # Disable in tests
```

Load in tests:
```python
from dotenv import load_dotenv
load_dotenv('.env.test')
```

## Test Coverage Goals

| Component | Target Coverage | Current |
|-----------|----------------|---------|
| Routes | 90% | ~30% |
| Services | 85% | ~40% |
| Models | 80% | ~0% |
| Auth | 95% | ~20% |
| Middleware | 85% | ~0% |
| **Overall** | **85%** | **~25%** |

## Testing Best Practices

### 1. Use Fixtures for Common Setup

Create `tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.database import get_db
from app.models import Base

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="module")
def client():
    """Test client for API calls"""
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def mock_asterisk_service():
    """Mock Asterisk service for testing"""
    service = MagicMock()
    service.originate_call = AsyncMock(return_value={
        "success": True,
        "call_id": "test-call-id",
        "phone_number": "1234567890",
        "channel": "Local/1234567890@outbound-ivr",
    })
    service.is_connected = AsyncMock(return_value=True)
    return service

@pytest.fixture
def auth_headers(client):
    """Get authentication headers for protected endpoints"""
    # Create test user first
    # Then get token
    response = client.post(
        "/api/v2/token",
        data={"username": "test_user", "password": "test_pass"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

### 2. Test Organization

Organize tests by functionality:

```python
class TestAuthentication:
    """Tests for authentication endpoints"""
    
    def test_login_success(self, client):
        """Test successful login"""
        pass
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        pass
    
    def test_token_expiration(self, client):
        """Test expired token handling"""
        pass

class TestCallOrigination:
    """Tests for call origination"""
    
    def test_originate_call_success(self, client, auth_headers):
        """Test successful call origination"""
        pass
    
    def test_originate_call_invalid_number(self, client, auth_headers):
        """Test call with invalid phone number"""
        pass
```

### 3. Mock External Dependencies

Always mock Asterisk ARI calls:

```python
@pytest.mark.asyncio
async def test_call_origination_with_mock(mock_asterisk_service):
    """Test call origination with mocked Asterisk"""
    result = await mock_asterisk_service.originate_call(
        phone_number="1234567890"
    )
    assert result["success"] is True
    mock_asterisk_service.originate_call.assert_called_once()
```

### 4. Test Edge Cases

```python
def test_rate_limiting(client):
    """Test rate limiting on token endpoint"""
    # Make 11 requests quickly (limit is 10)
    responses = []
    for i in range(11):
        response = client.post("/api/v2/token", data={
            "username": "test",
            "password": "test"
        })
        responses.append(response)
    
    # Last request should be rate limited
    assert responses[-1].status_code == 429

def test_long_phone_number(client, auth_headers):
    """Test phone number exceeding max length"""
    response = client.post(
        "/api/v2/interaction/12345678901234567890123456",
        headers=auth_headers
    )
    assert response.status_code == 422  # Validation error
```

### 5. Test Database Transactions

```python
def test_call_creation_rollback(client, db, auth_headers):
    """Test that failed calls don't leave orphaned records"""
    initial_count = db.query(Call).count()
    
    # Force an error during call creation
    with patch('app.services.asterisk.originate_call', side_effect=Exception("ARI error")):
        response = client.post(
            "/api/v2/interaction/1234567890",
            headers=auth_headers
        )
        assert response.status_code == 500
    
    # Check that no call was persisted
    final_count = db.query(Call).count()
    assert final_count == initial_count
```

## Integration Tests

### Test with Real Database

```python
@pytest.mark.integration
def test_full_call_lifecycle_with_db():
    """Integration test with real PostgreSQL"""
    # Requires test database setup
    pass
```

Run integration tests separately:
```bash
pytest -m integration
```

## Performance Tests

### Load Testing with Locust

Create `locustfile.py`:

```python
from locust import HttpUser, task, between

class ContactCenterUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Get auth token"""
        response = self.client.post("/api/v2/token", data={
            "username": "test_user",
            "password": "test_pass"
        })
        self.token = response.json()["access_token"]
    
    @task(3)
    def originate_call(self):
        """Originate a call"""
        self.client.post(
            "/api/v2/interaction/1234567890",
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(1)
    def check_health(self):
        """Check API health"""
        self.client.get("/health")
```

Run load test:
```bash
locust -f locustfile.py --host=http://localhost:8000
```

## Continuous Integration

### GitHub Actions Example

`.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_pass
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:test_pass@localhost:5432/test_db
        run: |
          pytest --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Test Checklist

- [ ] Unit tests for all routes
- [ ] Unit tests for all services
- [ ] Unit tests for authentication
- [ ] Integration tests with database
- [ ] Mock tests for Asterisk ARI
- [ ] Edge case tests
- [ ] Rate limiting tests
- [ ] Error handling tests
- [ ] Performance/load tests
- [ ] Security tests
- [ ] Coverage > 85%

## Debugging Tests

### Use pytest debugger:
```bash
pytest --pdb  # Drop into debugger on failure
pytest --pdb --maxfail=1  # Stop on first failure
```

### Print output:
```python
def test_something(client):
    response = client.get("/health")
    print(f"Response: {response.json()}")  # Will show with -s flag
    assert response.status_code == 200
```

### Log capture:
```bash
pytest --log-cli-level=DEBUG  # Show all logs
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Locust Documentation](https://docs.locust.io/)
