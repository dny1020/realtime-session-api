# Contributing to Contact Center API

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- Docker & Docker Compose (optional, for testing)
- Basic understanding of FastAPI, SQLAlchemy, and async Python

### Development Setup

1. **Fork and clone the repository:**

```bash
git clone https://github.com/YOUR_USERNAME/api-contact-center.git
cd api-contact-center
```

2. **Create a virtual environment:**

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. **Set up environment variables:**

```bash
cp .env.example .env
# Edit .env with test values
```

For local development, use minimal configuration:
```env
DISABLE_DB=true
SECRET_KEY=local-dev-secret-key
ARI_HTTP_URL=http://localhost:8088/ari
ARI_USERNAME=test
ARI_PASSWORD=test
ARI_APP=contactcenter
DEBUG=true
```

5. **Run the development server:**

```bash
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` to see the API documentation.

## Development Workflow

### 1. Create a Branch

Always create a new branch for your changes:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

**Branch naming conventions:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Adding or updating tests
- `chore/` - Maintenance tasks

### 2. Make Your Changes

Follow these guidelines:

- **Code style:** Follow PEP 8, use Black for formatting
- **Type hints:** Use type hints for function parameters and return values
- **Documentation:** Add docstrings to functions and classes
- **Tests:** Write tests for new functionality
- **Commits:** Make small, focused commits with clear messages

### 3. Code Quality Checks

Before committing, ensure your code passes all checks:

```bash
# Format code
black app/ config/ tests/

# Lint code
ruff check app/ config/ tests/

# Type checking (optional)
mypy app/ config/

# Run tests
make test

# Or with coverage
make test-cov
```

### 4. Commit Your Changes

Use conventional commit messages:

```bash
git commit -m "feat: add new endpoint for call statistics"
git commit -m "fix: resolve database connection timeout"
git commit -m "docs: update API usage examples"
git commit -m "test: add integration tests for call flow"
```

**Commit message format:**
```
<type>: <description>

[optional body]

[optional footer]
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only
- `style` - Code style changes (formatting)
- `refactor` - Code refactoring
- `test` - Adding or updating tests
- `chore` - Maintenance tasks
- `perf` - Performance improvements

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then open a Pull Request on GitHub with:
- Clear title describing the change
- Description explaining what and why
- Reference any related issues
- Screenshots/examples if applicable

## Code Style Guide

### Python Style

- **Line length:** 100 characters max
- **Formatting:** Use Black with default settings
- **Imports:** Group and sort (stdlib, third-party, local)
- **Naming:**
  - Functions/variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_CASE`
  - Private: `_leading_underscore`

### Example Code

```python
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.call import Call


router = APIRouter()


@router.get("/calls/{call_id}")
async def get_call_status(
    call_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """
    Retrieve the status of a specific call.
    
    Args:
        call_id: Unique identifier for the call
        db: Database session
        
    Returns:
        Dict containing call status information
        
    Raises:
        HTTPException: If call not found
    """
    call = db.query(Call).filter(Call.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {
        "call_id": call.call_id,
        "status": call.status.value,
        "phone_number": call.phone_number
    }
```

### Documentation Strings

Use Google-style docstrings:

```python
def process_call(phone_number: str, context: str = "default") -> dict:
    """
    Process an outbound call request.
    
    Args:
        phone_number: Phone number to call in E.164 format
        context: Asterisk context for the call
        
    Returns:
        Dictionary containing call information:
            - call_id: Unique identifier
            - status: Current call status
            
    Raises:
        ValueError: If phone_number is invalid
        
    Example:
        >>> process_call("+1234567890", "outbound")
        {'call_id': 'abc123', 'status': 'pending'}
    """
    pass
```

## Testing Guidelines

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use descriptive test names

```python
def test_call_creation_with_valid_phone_number():
    """Test that a call is created successfully with a valid phone number."""
    # Arrange
    phone_number = "+1234567890"
    
    # Act
    result = create_call(phone_number)
    
    # Assert
    assert result["success"] is True
    assert "call_id" in result
```

### Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── test_simple.py           # Basic import tests
├── test_api.py              # API endpoint tests
└── integration/             # Integration tests (future)
    └── test_call_flow.py
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run only fast tests (exclude slow/integration)
pytest tests/ -v -m "not slow"
```

## Pull Request Guidelines

### Before Submitting

- [ ] Code follows the project style guide
- [ ] All tests pass (`make test`)
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] Commit messages follow conventions
- [ ] Branch is up to date with main

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested your changes

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings

## Related Issues
Fixes #123
```

### Review Process

1. **Automated checks** run on every PR (tests, linting)
2. **Code review** by maintainer
3. **Changes requested** (if needed)
4. **Approval** and merge

## Project Structure

Understanding the codebase:

```
api_contact_center/
├── app/
│   ├── auth/              # Authentication logic
│   │   ├── jwt.py        # JWT token handling
│   │   └── create_user.py
│   ├── models/            # Database models
│   │   ├── call.py
│   │   └── user.py
│   ├── routes/            # API endpoints
│   │   ├── auth.py
│   │   └── interaction.py
│   ├── services/          # Business logic
│   │   └── asterisk.py   # Asterisk ARI integration
│   ├── middleware/        # HTTP middleware
│   ├── database.py        # Database configuration
│   └── main.py           # Application entry point
├── config/
│   └── settings.py       # Configuration management
├── tests/                # Test suite
├── alembic/              # Database migrations
├── .github/
│   └── workflows/        # CI/CD pipelines
└── docs/                 # Additional documentation
```

## Common Development Tasks

### Adding a New Endpoint

1. Create route in `app/routes/`:
```python
@router.post("/new-endpoint")
async def new_endpoint(
    data: RequestModel,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    # Implementation
    pass
```

2. Add tests in `tests/`:
```python
def test_new_endpoint_success():
    # Test implementation
    pass
```

3. Update documentation if needed

### Adding a Database Model

1. Create model in `app/models/`:
```python
class NewModel(Base):
    __tablename__ = "new_table"
    id = Column(Integer, primary_key=True)
    # fields
```

2. Create migration:
```bash
make migrate-create MSG="add new_table"
```

3. Apply migration:
```bash
make migrate
```

### Adding a Dependency

1. Add to `requirements.txt` (production) or `requirements-dev.txt` (development)
2. Update in virtual environment:
```bash
pip install -r requirements.txt
```

3. If it affects Docker, rebuild:
```bash
docker-compose build
```

## Getting Help

- **Questions:** Open a [Discussion](https://github.com/dny1020/api-contact-center/discussions)
- **Bugs:** Create an [Issue](https://github.com/dny1020/api-contact-center/issues)
- **Security:** Email security concerns (don't open public issues)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in the project documentation. Thank you for helping improve the Contact Center API!
