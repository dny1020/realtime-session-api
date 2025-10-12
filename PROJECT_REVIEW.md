# Python Project Best Practices Review & Improvements

**Project:** Contact Center API  
**Date:** 2025-01-06  
**Python Version:** 3.12  
**Framework:** FastAPI 0.117+

---

## 📋 Executive Summary

**Current State:** Good foundation with room for improvements  
**Overall Grade:** B+ (85/100)

**Strengths:**
- ✅ Clean FastAPI project structure
- ✅ Docker and docker-compose setup
- ✅ CI/CD with GitHub Actions
- ✅ Basic testing infrastructure
- ✅ Environment variable management

**Areas for Improvement:**
- ⚠️ Missing pyproject.toml (modern Python standard)
- ⚠️ No development vs production dependencies separation
- ⚠️ Limited test coverage
- ⚠️ No pre-commit hooks
- ⚠️ Missing VS Code configuration
- ⚠️ No branch protection templates

---

## 1️⃣ Virtual Environment Management

### Current State
- ✅ `.venv` in .gitignore
- ✅ `requirements.txt` exists
- ⚠️ No `requirements-dev.txt`
- ❌ No `pyproject.toml`

### Recommended Improvements

#### 1.1 Create `pyproject.toml` (Modern Python Standard)

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "contact-center-api"
version = "1.0.0"
description = "Production-ready Contact Center API with Asterisk ARI"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
keywords = ["fastapi", "asterisk", "ari", "contact-center", "ivr"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Framework :: FastAPI",
]

dependencies = [
    "fastapi>=0.117.1",
    "uvicorn>=0.36.0",
    "pydantic>=2.11.9",
    "pydantic-settings>=2.10.1",
    "SQLAlchemy>=2.0.43",
    "psycopg2-binary>=2.9.10",
    "httpx>=0.28.1",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.20",
    "loguru>=0.7.3",
    "python-dotenv>=1.1.1",
    "websockets>=12.0",
    "alembic>=1.13.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.1",
    "pytest-mock>=3.12.0",
    "black>=23.12.0",
    "ruff>=0.1.9",
    "mypy>=1.8.0",
    "pre-commit>=3.6.0",
    "httpx",
]

[project.urls]
Homepage = "https://github.com/YOUR_USERNAME/api_contact_center"
Repository = "https://github.com/YOUR_USERNAME/api_contact_center"
Documentation = "https://github.com/YOUR_USERNAME/api_contact_center#readme"
Issues = "https://github.com/YOUR_USERNAME/api_contact_center/issues"

[tool.black]
line-length = 100
target-version = ['py312']
include = '\.pyi?$'
exclude = '''
/(
    \.git
  | \.venv
  | venv
  | build
  | dist
  | __pycache__
  | migrations
)/
'''

[tool.ruff]
line-length = 100
target-version = "py312"
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = ["E501", "B008", "C901"]
exclude = [".venv", "venv", "migrations"]

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
ignore_missing_imports = true
exclude = ["venv", ".venv", "tests"]

[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers"
pythonpath = "."
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]

[tool.coverage.run]
source = ["app"]
omit = ["tests/*", "venv/*", ".venv/*", "*/migrations/*"]

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = false
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

#### 1.2 Split Dependencies

**requirements.txt** (Production)
```txt
# Production dependencies only
fastapi==0.117.1
uvicorn[standard]==0.36.0
pydantic==2.11.9
pydantic-settings==2.10.1
SQLAlchemy==2.0.43
psycopg2-binary==2.9.10
httpx==0.28.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.20
loguru==0.7.3
python-dotenv==1.1.1
websockets==12.0
alembic==1.13.1
```

**requirements-dev.txt** (Development)
```txt
-r requirements.txt

# Testing
pytest==7.4.3
pytest-cov==4.1.0
pytest-asyncio==0.21.1
pytest-mock==3.12.0
pytest-xdist==3.5.0

# Code Quality
black==23.12.1
ruff==0.1.15
mypy==1.8.0
pre-commit==3.6.0

# Development Tools
ipython==8.19.0
ipdb==0.13.13
watchdog==4.0.0
```

#### 1.3 Improve .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environments
venv/
ENV/
env/
.venv/
.env/

# Environment Variables
.env
.env.local
.env.*.local
*.env

# IDE - VSCode
.vscode/*
!.vscode/settings.json
!.vscode/tasks.json
!.vscode/launch.json
!.vscode/extensions.json
*.code-workspace

# IDE - PyCharm
.idea/
*.iml
*.iws
*.ipr

# IDE - Others
*.swp
*.swo
*~
.DS_Store

# Testing
.pytest_cache/
.coverage
.coverage.*
htmlcov/
.tox/
.nox/
coverage.xml
*.cover
.hypothesis/

# Type Checking
.mypy_cache/
.dmypy.json
dmypy.json
.pyre/
.pytype/

# Logs
*.log
logs/
*.log.*

# Database
*.db
*.sqlite3
*.sqlite

# Project Specific
uploads/
audio/
backups/

# Docker
*.pid
.dockerignore

# OS
Thumbs.db
.DS_Store
*.bak
*.tmp

# Alembic
alembic/versions/*.pyc

# Security
secrets/
*.pem
*.key
certificates/
```

---

## 2️⃣ Code Structure and Modularization

### Current State
- ✅ Good FastAPI structure
- ✅ Separation of concerns (routes, services, models)
- ⚠️ Missing dependency injection
- ⚠️ No shared schemas/DTOs

### Recommended Improvements

#### 2.1 Enhanced Project Structure

```
api_contact_center/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/                    # NEW: Core functionality
│   │   ├── __init__.py
│   │   ├── config.py            # Centralized config
│   │   ├── security.py          # Security utilities
│   │   └── dependencies.py      # FastAPI dependencies
│   ├── api/                     # Rename 'routes' to 'api'
│   │   ├── __init__.py
│   │   ├── deps.py              # API dependencies
│   │   └── v2/                  # API versioning
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── calls.py
│   │       └── health.py
│   ├── models/                  # Database models (ORM)
│   │   ├── __init__.py
│   │   ├── base.py              # NEW: Base model
│   │   ├── call.py
│   │   └── user.py
│   ├── schemas/                 # NEW: Pydantic schemas (DTOs)
│   │   ├── __init__.py
│   │   ├── call.py
│   │   ├── user.py
│   │   └── token.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── asterisk.py
│   │   ├── call_service.py      # NEW: Business logic
│   │   └── auth_service.py      # NEW: Auth logic
│   ├── db/                      # NEW: Database package
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── session.py
│   │   └── repositories/        # NEW: Repository pattern
│   │       ├── __init__.py
│   │       ├── call.py
│   │       └── user.py
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── logging.py
│   │   ├── error_handler.py     # NEW
│   │   └── rate_limit.py        # NEW
│   └── utils/                   # NEW: Utility functions
│       ├── __init__.py
│       ├── datetime.py
│       └── validators.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/                    # NEW: Unit tests
│   │   ├── __init__.py
│   │   ├── test_services.py
│   │   └── test_utils.py
│   ├── integration/             # NEW: Integration tests
│   │   ├── __init__.py
│   │   ├── test_api.py
│   │   └── test_database.py
│   └── fixtures/                # NEW: Test fixtures
│       ├── __init__.py
│       └── factories.py
├── alembic/
├── scripts/                     # NEW: Utility scripts
│   ├── create_user.py
│   ├── seed_data.py
│   └── check_health.py
├── docs/                        # NEW: Documentation
│   ├── api.md
│   ├── deployment.md
│   └── development.md
├── .vscode/                     # NEW: VS Code config
│   ├── settings.json
│   ├── launch.json
│   └── extensions.json
├── .github/
│   ├── workflows/
│   ├── PULL_REQUEST_TEMPLATE.md # NEW
│   └── ISSUE_TEMPLATE/          # NEW
│       ├── bug_report.md
│       └── feature_request.md
├── pyproject.toml               # NEW
├── requirements.txt
├── requirements-dev.txt         # NEW
├── .pre-commit-config.yaml      # NEW
├── .env.example
├── README.md
├── CONTRIBUTING.md              # NEW
├── CHANGELOG.md                 # NEW
└── LICENSE                      # NEW
```

#### 2.2 Create Base Model

```python
# app/models/base.py
from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.ext.declarative import declared_attr
from app.db.base import Base


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps"""
    
    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=datetime.utcnow, nullable=False)
    
    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime, 
            default=datetime.utcnow, 
            onupdate=datetime.utcnow, 
            nullable=False
        )


class BaseModel(Base, TimestampMixin):
    """Base model with common fields"""
    __abstract__ = True
```

#### 2.3 Create Schemas (DTOs)

```python
# app/schemas/call.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.call import CallStatus


class CallBase(BaseModel):
    """Base call schema"""
    phone_number: str = Field(..., min_length=7, max_length=20)
    context: Optional[str] = Field(default="outbound-ivr")
    extension: Optional[str] = Field(default="s")
    priority: Optional[int] = Field(default=1, ge=1)
    timeout: Optional[int] = Field(default=30000, gt=0)
    caller_id: Optional[str] = Field(default="Outbound Call")


class CallCreate(CallBase):
    """Schema for creating a call"""
    variables: Optional[dict] = None


class CallResponse(BaseModel):
    """Schema for call response"""
    model_config = ConfigDict(from_attributes=True)
    
    call_id: str
    phone_number: str
    status: CallStatus
    channel: Optional[str] = None
    created_at: datetime
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration: Optional[int] = None
    failure_reason: Optional[str] = None


class CallStatusResponse(BaseModel):
    """Schema for call status"""
    model_config = ConfigDict(from_attributes=True)
    
    call_id: str
    status: CallStatus
    is_active: bool
    is_completed: bool
```

#### 2.4 Dependency Injection

```python
# app/core/dependencies.py
from typing import Generator, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.security import decode_access_token
from app.models.user import User
from app.db.repositories.user import UserRepository


security = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    username = payload.get("sub")
    user_repo = UserRepository(db)
    user = user_repo.get_by_username(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


# Type aliases for cleaner code
DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
```

---

## 3️⃣ Testing with pytest

### Current State
- ✅ Basic pytest setup
- ✅ Test files present
- ⚠️ Limited test coverage (~27%)
- ❌ No test organization
- ❌ No fixtures for common scenarios

### Recommended Improvements

#### 3.1 Enhanced conftest.py

```python
# tests/conftest.py
import pytest
import os
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.core.dependencies import get_db
from app.models.user import User
from app.models.call import Call, CallStatus


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    """Create database engine for tests"""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(db_engine) -> Generator[Session, None, None]:
    """Create a fresh database session for each test"""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Create test client with overridden database"""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user"""
    from app.auth.jwt import get_password_hash
    
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test User"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Get authentication headers for test user"""
    from app.auth.jwt import create_access_token
    
    token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_call(db: Session, test_user: User) -> Call:
    """Create a test call"""
    call = Call(
        call_id="test-call-123",
        phone_number="+1234567890",
        status=CallStatus.PENDING,
        context="outbound-ivr",
        extension="s",
        priority=1,
        timeout=30000,
        caller_id="Test Call",
        user_id=test_user.id
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


# Markers
def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
```

#### 3.2 Test Organization

```python
# tests/unit/test_call_service.py
import pytest
from unittest.mock import Mock, patch
from app.services.call_service import CallService
from app.models.call import CallStatus


@pytest.mark.unit
class TestCallService:
    """Unit tests for CallService"""
    
    def test_create_call_success(self, db):
        """Test creating a call successfully"""
        service = CallService(db)
        call = service.create_call(
            phone_number="+1234567890",
            context="outbound-ivr"
        )
        assert call.call_id is not None
        assert call.status == CallStatus.PENDING
    
    def test_create_call_invalid_phone(self, db):
        """Test creating call with invalid phone number"""
        service = CallService(db)
        with pytest.raises(ValueError):
            service.create_call(phone_number="invalid")


# tests/integration/test_call_api.py
import pytest


@pytest.mark.integration
class TestCallAPI:
    """Integration tests for Call API"""
    
    def test_create_call_endpoint(self, client, auth_headers):
        """Test POST /api/v2/calls endpoint"""
        response = client.post(
            "/api/v2/calls",
            headers=auth_headers,
            json={
                "phone_number": "+1234567890",
                "context": "outbound-ivr"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "call_id" in data
    
    def test_get_call_status(self, client, auth_headers, test_call):
        """Test GET /api/v2/calls/{call_id} endpoint"""
        response = client.get(
            f"/api/v2/calls/{test_call.call_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["call_id"] == test_call.call_id
```

#### 3.3 Coverage Configuration

```ini
# .coveragerc
[run]
source = app
omit =
    tests/*
    venv/*
    .venv/*
    */migrations/*
    */alembic/*
    app/__init__.py

[report]
precision = 2
show_missing = True
skip_covered = False
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__:
    if TYPE_CHECKING:
    @abstractmethod

[html]
directory = htmlcov
```

---

## 4️⃣ Version Control Hygiene

### Current State
- ✅ Git initialized
- ⚠️ No branch protection
- ⚠️ No commit conventions
- ❌ No PR templates

### Recommended Improvements

#### 4.1 Commit Message Convention

```bash
# .gitmessage
# <type>(<scope>): <subject>
#
# <body>
#
# <footer>
#
# Types:
# feat: A new feature
# fix: A bug fix
# docs: Documentation only changes
# style: Changes that don't affect code meaning
# refactor: Code change that neither fixes a bug nor adds a feature
# perf: Performance improvement
# test: Adding missing tests
# chore: Changes to build process or auxiliary tools
#
# Example:
# feat(api): add call status webhook endpoint
#
# - Added new endpoint POST /api/v2/webhooks/call-status
# - Implemented signature verification
# - Added tests for webhook handler
#
# Closes #123
```

Configure git to use this template:
```bash
git config commit.template .gitmessage
```

#### 4.2 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-json
      - id: check-toml
      - id: check-merge-conflict
      - id: detect-private-key
      - id: mixed-line-ending

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.12

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.15
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--ignore-missing-imports]

  - repo: https://github.com/python-poetry/poetry
    rev: 1.7.0
    hooks:
      - id: poetry-check
      - id: poetry-lock
        args: [--no-update]
```

Install:
```bash
pre-commit install
pre-commit run --all-files
```

#### 4.3 Pull Request Template

```markdown
# .github/PULL_REQUEST_TEMPLATE.md
## Description
<!-- Provide a brief description of the changes -->

## Type of Change
<!-- Mark the relevant option with an [x] -->
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Related Issues
<!-- Link to related issues using #issue_number -->
Closes #

## Changes Made
<!-- List the specific changes made in this PR -->
- 
- 
- 

## Testing
<!-- Describe the tests you ran to verify your changes -->
- [ ] Unit tests pass locally
- [ ] Integration tests pass locally
- [ ] Manual testing performed
- [ ] Test coverage maintained or improved

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Screenshots (if applicable)
<!-- Add screenshots to help explain your changes -->

## Additional Notes
<!-- Add any additional notes or context about the PR -->
```

#### 4.4 Issue Templates

```yaml
# .github/ISSUE_TEMPLATE/bug_report.md
---
name: Bug Report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Make request to '...'
2. With payload '....'
3. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Actual behavior**
What actually happened.

**Environment:**
- OS: [e.g. Ubuntu 22.04]
- Python version: [e.g. 3.12.1]
- FastAPI version: [e.g. 0.117.1]
- Docker version (if applicable): [e.g. 24.0.0]

**Logs**
```
Paste relevant logs here
```

**Additional context**
Add any other context about the problem here.
```

#### 4.5 Semantic Versioning

```markdown
# CHANGELOG.md
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Feature X

### Changed
- Updated Y

### Fixed
- Bug Z

## [1.0.0] - 2025-01-06

### Added
- Initial release
- Call origination via Asterisk ARI
- Real-time WebSocket call status updates
- JWT authentication
- PostgreSQL persistence
- Docker and docker-compose support
- CI/CD with GitHub Actions

### Security
- Implemented bcrypt password hashing
- Added rate limiting on authentication endpoints
```

---

## 5️⃣ VS Code Setup

### Recommended Extensions

```json
// .vscode/extensions.json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "ms-python.mypy-type-checker",
    "tamasfe.even-better-toml",
    "redhat.vscode-yaml",
    "esbenp.prettier-vscode",
    "ms-azuretools.vscode-docker",
    "streetsidesoftware.code-spell-checker",
    "eamodio.gitlens",
    "GitHub.copilot",
    "GitHub.vscode-pull-request-github",
    "njpwerner.autodocstring",
    "mechatroner.rainbow-csv",
    "usernamehw.errorlens"
  ]
}
```

### VS Code Settings

```json
// .vscode/settings.json
{
  // Python
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.languageServer": "Pylance",
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.autoImportCompletions": true,
  "python.analysis.diagnosticMode": "workspace",
  
  // Formatting
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "black-formatter.args": [
    "--line-length=100"
  ],
  
  // Linting
  "ruff.args": [
    "--line-length=100"
  ],
  "ruff.lint.run": "onSave",
  
  // Type Checking
  "mypy-type-checker.args": [
    "--ignore-missing-imports"
  ],
  
  // Files
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/.pytest_cache": true,
    "**/.mypy_cache": true,
    "**/.ruff_cache": true
  },
  "files.watcherExclude": {
    "**/.venv/**": true,
    "**/venv/**": true
  },
  
  // Editor
  "editor.rulers": [100],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  
  // Testing
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": [
    "tests"
  ],
  
  // Terminal
  "terminal.integrated.env.linux": {
    "PYTHONPATH": "${workspaceFolder}"
  },
  "terminal.integrated.env.osx": {
    "PYTHONPATH": "${workspaceFolder}"
  },
  "terminal.integrated.env.windows": {
    "PYTHONPATH": "${workspaceFolder}"
  }
}
```

### VS Code Tasks

```json
// .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run Tests",
      "type": "shell",
      "command": "make test",
      "group": {
        "kind": "test",
        "isDefault": true
      },
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    },
    {
      "label": "Run Tests with Coverage",
      "type": "shell",
      "command": "make test-cov",
      "group": "test",
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    },
    {
      "label": "Format Code",
      "type": "shell",
      "command": "black app/ tests/ config/",
      "group": "build"
    },
    {
      "label": "Lint Code",
      "type": "shell",
      "command": "ruff check app/ tests/ config/",
      "group": "build"
    },
    {
      "label": "Start Dev Server",
      "type": "shell",
      "command": "make dev",
      "isBackground": true,
      "problemMatcher": []
    },
    {
      "label": "Start Docker Services",
      "type": "shell",
      "command": "make up",
      "group": "build"
    }
  ]
}
```

### VS Code Launch Configuration

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "jinja": true,
      "justMyCode": false,
      "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "DEBUG": "true"
      }
    },
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "justMyCode": false
    },
    {
      "name": "Python: Pytest Current File",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "${file}",
        "-v"
      ],
      "console": "integratedTerminal",
      "justMyCode": false,
      "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "DISABLE_DB": "true"
      }
    },
    {
      "name": "Python: Pytest All",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "tests/",
        "-v",
        "--tb=short"
      ],
      "console": "integratedTerminal",
      "justMyCode": false,
      "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "DISABLE_DB": "true"
      }
    }
  ]
}
```

---

## 6️⃣ GitHub Workflows Enhancement

### Current State
- ✅ Basic CI/CD setup
- ⚠️ Missing code quality checks
- ⚠️ No caching optimization

### Recommended Improvements

#### 6.1 Enhanced CI/CD Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: "3.12"

jobs:
  lint:
    name: Lint Code
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install black ruff mypy
      
      - name: Check formatting with Black
        run: black --check app/ tests/ config/
      
      - name: Lint with Ruff
        run: ruff check app/ tests/ config/
      
      - name: Type check with MyPy
        run: mypy app/ config/ --ignore-missing-imports
        continue-on-error: true

  test:
    name: Test (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run tests with coverage
        env:
          PYTHONPATH: "."
          DISABLE_DB: "true"
          SECRET_KEY: "test-secret-key"
        run: |
          pytest tests/ -v --cov=app --cov-report=xml --cov-report=term
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        if: matrix.python-version == '3.12'
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage.xml
          fail_ci_if_error: false

  security:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Bandit security scan
        uses: tj-actions/bandit@v5.1
        with:
          targets: app/
          
      - name: Run Safety check
        run: |
          pip install safety
          safety check --json

  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: [lint, test]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Build Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          tags: contact-center-api:test
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

---

## 7️⃣ Documentation Improvements

### Enhanced README.md Structure

```markdown
# Contact Center API

[![CI](https://github.com/YOUR_USERNAME/api_contact_center/workflows/CI/badge.svg)](https://github.com/YOUR_USERNAME/api_contact_center/actions)
[![codecov](https://codecov.io/gh/YOUR_USERNAME/api_contact_center/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/api_contact_center)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.117+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> Production-ready FastAPI service for single outbound IVR calls via Asterisk ARI with real-time WebSocket status updates.

## ✨ Features

- 🎯 Single call origination to specific numbers
- 📊 Real-time status updates via WebSocket
- 🔐 JWT authentication with bcrypt
- 🗄️ PostgreSQL persistence
- 🐳 Docker ready with multi-platform images
- 🚀 CI/CD with GitHub Actions
- 📝 RESTful API with OpenAPI docs
- ✅ Comprehensive test suite

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Asterisk server with ARI enabled

### Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/api_contact_center.git
cd api_contact_center
```

2. Create virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
# For development:
pip install -r requirements-dev.txt
```

4. Set up environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run with Make (recommended):
```bash
make quick-start  # Sets up everything
```

Or manually:
```bash
docker-compose up -d
make migrate
make user
```

## 📚 API Documentation

Interactive API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v2/token` | Get JWT token |
| POST | `/api/v2/calls` | Create outbound call |
| GET | `/api/v2/calls/{call_id}` | Get call status |
| GET | `/health` | Health check |

See [API Documentation](docs/api.md) for detailed information.

## 💻 Development

### Project Structure

```
app/
├── api/          # API routes
├── core/         # Core functionality
├── db/           # Database
├── models/       # ORM models
├── schemas/      # Pydantic schemas
├── services/     # Business logic
└── utils/        # Utilities
```

### Development Workflow

```bash
# Install pre-commit hooks
pre-commit install

# Run development server
make dev

# Run tests
make test

# Format code
make format

# Lint code
make lint

# Type check
mypy app/
```

## 🧪 Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/unit/test_services.py -v

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v
```

## 🚢 Deployment

See [Deployment Guide](docs/deployment.md) for detailed instructions.

### Docker

```bash
# Build image
docker build -t contact-center-api .

# Run container
docker run -p 8000:8000 contact-center-api
```

### Docker Compose

```bash
docker-compose up -d
```

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

### Quick Guidelines

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (following [conventional commits](https://www.conventionalcommits.org/))
6. Push to the branch
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Asterisk](https://www.asterisk.org/)

## 📞 Support

- Documentation: [docs/](docs/)
- Issues: [GitHub Issues](https://github.com/YOUR_USERNAME/api_contact_center/issues)
- Discussions: [GitHub Discussions](https://github.com/YOUR_USERNAME/api_contact_center/discussions)

---

Made with ❤️ by [Your Name]
```

### CONTRIBUTING.md

```markdown
# Contributing to Contact Center API

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Code of Conduct

Be respectful, inclusive, and professional in all interactions.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/api_contact_center.git`
3. Create a branch: `git checkout -b feature/my-feature`
4. Make your changes
5. Test your changes
6. Submit a pull request

## Development Setup

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
make test
```

## Code Style

- Follow PEP 8
- Use Black for formatting (line length: 100)
- Use Ruff for linting
- Add type hints where possible
- Write docstrings for all public functions/classes

## Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

Example:
```
feat(api): add webhook support for call status

- Implemented POST /api/v2/webhooks/call-status
- Added signature verification
- Added comprehensive tests

Closes #123
```

## Testing

- Write tests for new features
- Maintain or improve test coverage
- Run tests before submitting: `make test`
- Use descriptive test names

## Pull Request Process

1. Update documentation
2. Add tests for new features
3. Ensure all tests pass
4. Update CHANGELOG.md
5. Get approval from maintainers
6. Squash commits if requested

## Questions?

Open an issue or start a discussion on GitHub.
```

---

## 📊 Summary of Improvements

### Priority Matrix

| Category | Current Grade | Target Grade | Priority | Effort |
|----------|--------------|--------------|----------|--------|
| Virtual Environment | B | A+ | High | Low |
| Code Structure | B+ | A | Medium | Medium |
| Testing | C | A- | High | High |
| Version Control | C+ | A | High | Low |
| VS Code Setup | F | A+ | Medium | Low |
| GitHub Workflows | B | A | Medium | Medium |
| Documentation | B- | A | Medium | Medium |

### Action Plan

**Week 1: Foundation (High Priority, Low Effort)**
1. ✅ Create `pyproject.toml`
2. ✅ Split dependencies (requirements-dev.txt)
3. ✅ Add `.pre-commit-config.yaml`
4. ✅ Install pre-commit hooks
5. ✅ Create VS Code configuration files
6. ✅ Add PR and Issue templates

**Week 2: Code Quality (High Priority, Medium Effort)**
1. ✅ Set up Black, Ruff, MyPy
2. ✅ Create shared schemas/DTOs
3. ✅ Implement dependency injection
4. ✅ Add base models
5. ✅ Enhance .gitignore

**Week 3: Testing (High Priority, High Effort)**
1. ✅ Reorganize tests (unit/integration)
2. ✅ Enhance conftest.py with fixtures
3. ✅ Write more unit tests (target 80% coverage)
4. ✅ Add integration tests
5. ✅ Configure coverage reporting

**Week 4: Documentation & Polish (Medium Priority)**
1. ✅ Enhance README.md
2. ✅ Create CONTRIBUTING.md
3. ✅ Add CHANGELOG.md
4. ✅ Improve GitHub workflows
5. ✅ Add security scanning

---

## 🎯 Next Steps

1. **Immediate Actions** (Today):
   - Create `pyproject.toml`
   - Add `.vscode/` configuration
   - Install pre-commit hooks

2. **This Week**:
   - Implement pre-commit hooks
   - Add development dependencies
   - Create PR/Issue templates

3. **This Month**:
   - Increase test coverage to 80%+
   - Implement all code quality tools
   - Complete documentation

4. **Ongoing**:
   - Follow commit conventions
   - Maintain CHANGELOG.md
   - Review and update dependencies monthly

---

**End of Review**

Total Recommended Files to Add: 15+
Total Recommended Updates: 8
Estimated Implementation Time: 2-3 weeks
Expected Quality Improvement: B+ → A
