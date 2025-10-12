# Contact Center API

![CI/CD](https://github.com/dny1020/api-contact-center/workflows/CI%2FCD%20Pipeline/badge.svg)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Production-ready FastAPI service for **single outbound IVR calls** via Asterisk ARI with real-time WebSocket event tracking.

## ✨ Features

- 🎯 **Single call origination** - Trigger outbound calls to specific phone numbers
- 📡 **Real-time events** - WebSocket connection to Asterisk ARI for live status updates
- 🔐 **JWT authentication** - Secure access with bcrypt password hashing
- 🗄️ **PostgreSQL persistence** - Track call history and status
- 🐳 **Docker ready** - Multi-platform container images (amd64/arm64)
- 🚀 **CI/CD pipeline** - Automated testing and Docker builds via GitHub Actions
- 📝 **OpenAPI docs** - Interactive API documentation at `/docs`
- ⚡ **Production-ready** - Rate limiting, CORS, health checks, and structured logging

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose (for containerized deployment)
- Python 3.11+ (for local development)
- PostgreSQL 15+ (production mode)
- Asterisk with ARI enabled (external service)

### Option 1: Using Makefile (Recommended)

```bash
# Complete first-time setup
make quick-start

# Daily operations
make up          # Start services
make logs        # View logs
make test        # Run tests
make health      # Check API health
make down        # Stop services

# See all available commands
make help
```

### Option 2: Using Docker Compose

```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/dny1020/api-contact-center:latest

# Or start with docker-compose
docker-compose up -d
```

### Option 3: Local Development (No Docker)

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set minimal environment variables for local dev
export DISABLE_DB=true
export SECRET_KEY=local-dev-secret-key
export ARI_HTTP_URL=http://your-asterisk-server:8088/ari
export ARI_USERNAME=your_ari_user
export ARI_PASSWORD=your_ari_password
export ARI_APP=contactcenter

# Run the API
uvicorn app.main:app --reload
```

Access the API at `http://localhost:8000/docs`

## 📡 API Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v2/token` | Obtain JWT access token | No |
| POST | `/api/v2/interaction/{number}` | Initiate call to a phone number | Yes |
| GET | `/api/v2/status/{call_id}` | Get call status | Yes |
| POST | `/api/v2/calls` | Create call (RESTful alternative) | Yes |
| GET | `/api/v2/calls/{call_id}` | Get call details | Yes |
| GET | `/health` | Health check (DB + Asterisk) | No |
| GET | `/docs` | Swagger UI documentation | No |
| GET | `/redoc` | ReDoc documentation | No |

## 💡 Usage Example

### 1. Obtain Access Token

```bash
curl -X POST http://localhost:8000/api/v2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=yourpassword"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Initiate an Outbound Call

```bash
TOKEN="your_access_token_here"

curl -X POST http://localhost:8000/api/v2/interaction/+1234567890 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "context": "outbound-ivr",
    "extension": "s",
    "caller_id": "CompanyName <+1987654321>"
  }'
```

**Response:**
```json
{
  "call_id": "c4ca4238-a0b9-3382-8dcc-509a6f75849b",
  "status": "pending",
  "phone_number": "+1234567890",
  "created_at": "2024-10-12T14:30:00.123456",
  "message": "Call initiated successfully"
}
```

### 3. Check Call Status

```bash
curl -X GET http://localhost:8000/api/v2/status/c4ca4238-a0b9-3382-8dcc-509a6f75849b \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "call_id": "c4ca4238-a0b9-3382-8dcc-509a6f75849b",
  "phone_number": "+1234567890",
  "status": "answered",
  "created_at": "2024-10-12T14:30:00.123456",
  "dialed_at": "2024-10-12T14:30:01.234567",
  "answered_at": "2024-10-12T14:30:05.456789",
  "duration": 45,
  "context": "outbound-ivr",
  "extension": "s",
  "caller_id": "CompanyName <+1987654321>"
}
```

## 🏗️ Architecture

```
┌──────────────┐
│   Client     │
│  (cURL/App)  │
└──────┬───────┘
       │ HTTPS
       ▼
┌──────────────────────────────────────┐
│      FastAPI Application             │
│  ┌────────────────────────────────┐  │
│  │  JWT Auth + Rate Limiting      │  │
│  ├────────────────────────────────┤  │
│  │  REST Endpoints                │  │
│  │  /api/v2/interaction/{number}  │  │
│  │  /api/v2/status/{call_id}      │  │
│  │  /api/v2/calls                 │  │
│  └────────────────────────────────┘  │
└───────┬──────────────────────┬───────┘
        │                      │
        │ SQL (ORM)            │ HTTP + WebSocket
        ▼                      ▼
┌───────────────┐      ┌──────────────────┐
│  PostgreSQL   │      │  Asterisk ARI    │
│   (Persist    │      │  (External SIP   │
│   Call Data)  │      │   PBX Service)   │
└───────────────┘      └──────────────────┘
                               │
                               │ SIP/RTP
                               ▼
                       ┌──────────────────┐
                       │   Phone Network  │
                       │  (Outbound Call) │
                       └──────────────────┘
```

### Call Flow

**Status Progression:**
```
pending → dialing → ringing → answered → completed
                           ↘ busy
                           ↘ no_answer
                           ↘ failed
```

1. Client requests call via REST API
2. FastAPI validates JWT token and creates call record in PostgreSQL
3. FastAPI sends call origination request to Asterisk ARI (HTTP)
4. Asterisk establishes WebSocket connection and sends real-time events
5. FastAPI updates call status in database based on WebSocket events:
   - `StasisStart` → dialing
   - `ChannelStateChange` (Ringing) → ringing
   - `ChannelStateChange` (Up) → answered
   - `ChannelDestroyed` → completed/busy/no_answer/failed
6. Client can query updated status at any time via `/status/{call_id}`

## 🐳 Docker Images

Pre-built images are available on GitHub Container Registry:

```bash
# Pull latest stable version
docker pull ghcr.io/dny1020/api-contact-center:latest

# Pull specific version tag
docker pull ghcr.io/dny1020/api-contact-center:v1.0.0

# Pull development branch
docker pull ghcr.io/dny1020/api-contact-center:develop

# Pull by commit SHA (for debugging)
docker pull ghcr.io/dny1020/api-contact-center:main-abc1234
```

**Multi-platform support:** Images are built for `linux/amd64` and `linux/arm64`

### Building Locally

```bash
# Build for current platform
docker build -t api-contact-center:local .

# Build for multiple platforms (requires buildx)
docker buildx build --platform linux/amd64,linux/arm64 -t api-contact-center:multi .
```

## ⚙️ Configuration

Create a `.env` file from the example template:

```bash
cp .env.example .env
```

### Key Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Production only | - |
| `DISABLE_DB` | Run without database (testing) | No | `false` |
| `SECRET_KEY` | JWT signing key (64+ chars) | **Yes** | - |
| `ARI_HTTP_URL` | Asterisk ARI HTTP endpoint | **Yes** | - |
| `ARI_USERNAME` | Asterisk ARI username | **Yes** | - |
| `ARI_PASSWORD` | Asterisk ARI password | **Yes** | - |
| `ARI_APP` | Asterisk Stasis app name | **Yes** | `contactcenter` |
| `DEBUG` | Enable debug mode | No | `false` |
| `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) | No | `*` |

### Example Configuration

**.env file:**
```env
# Database (PostgreSQL required for production)
DATABASE_URL=postgresql://contact_center:secure_password@postgres:5432/contact_center_db

# Security (MUST change in production!)
SECRET_KEY=a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2

# Asterisk ARI Connection (external service)
ARI_HTTP_URL=http://asterisk-server.local:8088/ari
ARI_USERNAME=ari_user
ARI_PASSWORD=secure_ari_password
ARI_APP=contactcenter

# Call defaults
DEFAULT_CONTEXT=outbound-ivr
DEFAULT_EXTENSION=s
DEFAULT_PRIORITY=1
DEFAULT_TIMEOUT=30
DEFAULT_CALLER_ID=Contact Center

# Application
DEBUG=false
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### Minimal Setup (Local Development)

```env
# Run API without database
DISABLE_DB=true
SECRET_KEY=local-dev-only-secret-key
ARI_HTTP_URL=http://localhost:8088/ari
ARI_USERNAME=ariuser
ARI_PASSWORD=aripass
ARI_APP=contactcenter
DEBUG=true
```

## 🛠️ Development

### Local Setup

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development tools

# Run the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage report
make test-cov

# Run specific test file
PYTHONPATH=. DISABLE_DB=true SECRET_KEY=test pytest tests/test_api.py -v

# Run with detailed output
PYTHONPATH=. DISABLE_DB=true SECRET_KEY=test pytest tests/ -vv --tb=long
```

### Code Quality

```bash
# Format code with black
black app/ config/ tests/

# Lint with ruff
ruff check app/ config/ tests/

# Type checking (if using mypy)
mypy app/ config/ --ignore-missing-imports
```

### Database Migrations

```bash
# Create new migration
make migrate-create MSG="add new column to calls table"

# Apply migrations
make migrate

# Rollback last migration
make migrate-down

# View migration history
make migrate-history
```

## 🚀 CI/CD Pipeline

This project uses GitHub Actions for continuous integration and deployment.

### Automated Workflows

**On every push and pull request:**
- ✅ Run pytest test suite
- ✅ Generate code coverage reports
- ✅ Build Docker images for `linux/amd64` and `linux/arm64`
- ✅ Push images to GitHub Container Registry with smart tagging
- ✅ Security scanning with Trivy (on main branch)

### Workflow Files

- **`.github/workflows/ci-cd.yml`** - Main CI/CD pipeline
- **`.github/workflows/pr-checks.yml`** - Pull request validation
- **`.github/workflows/release.yml`** - Release automation

### Docker Image Tags

Images are automatically tagged based on the trigger:

| Event | Tag Example | Description |
|-------|-------------|-------------|
| Push to `main` | `latest`, `main-abc1234` | Latest stable + SHA |
| Push to `develop` | `develop`, `develop-abc1234` | Development + SHA |
| Version tag | `v1.2.3`, `1.2`, `1` | Semantic versioning |
| Pull request | `pr-123` | PR number |

### Manual Deployment

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Build and push
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/dny1020/api-contact-center:latest \
  --push .
```

## 📦 Tech Stack

### Core Framework
- **Python 3.11+** - Modern Python with type hints
- **FastAPI 0.117+** - High-performance async web framework
- **Uvicorn** - ASGI server for production

### Database & ORM
- **PostgreSQL 15+** - Production database
- **SQLAlchemy 2.0** - Modern async ORM
- **Alembic** - Database migrations

### Authentication & Security
- **JWT** (python-jose) - Token-based authentication
- **Bcrypt** (passlib) - Password hashing
- **Pydantic** - Input validation and settings management

### Telephony
- **Asterisk ARI** - WebSocket + HTTP for call control
- External Asterisk PBX server required (not included)

### DevOps & Tools
- **Docker** - Containerization
- **Docker Compose** - Local orchestration
- **GitHub Actions** - CI/CD automation
- **pytest** - Testing framework
- **pytest-cov** - Code coverage
- **black** - Code formatting
- **ruff** - Fast Python linter
- **Loguru** - Structured logging

### Optional (Production)
- **Nginx/Traefik** - Reverse proxy
- **Let's Encrypt** - SSL certificates

## 🔒 Security

This project implements multiple security layers:

- ✅ **JWT Authentication** - Secure token-based access control
- ✅ **Password Hashing** - Bcrypt with salt for password storage
- ✅ **Rate Limiting** - In-memory rate limiter on sensitive endpoints (10 req/60s on `/api/v2/token`)
- ✅ **Input Validation** - Pydantic models for all requests
- ✅ **SQL Injection Protection** - ORM-based queries only
- ✅ **CORS Configuration** - Configurable allowed origins
- ✅ **Non-root Docker User** - Container runs as unprivileged user
- ✅ **Security Scanning** - Trivy scans on every build
- ✅ **No Public ARI Exposure** - Asterisk ARI accessed internally only
- ✅ **Secrets Validation** - Startup checks for placeholder secrets

### Security Best Practices

**Production Checklist:**
- [ ] Set strong `SECRET_KEY` (64+ random characters)
- [ ] Use strong database passwords
- [ ] Enable HTTPS with valid SSL certificates
- [ ] Configure `ALLOWED_ORIGINS` to specific domains
- [ ] Keep dependencies updated (`pip install --upgrade`)
- [ ] Review Docker image security scan results
- [ ] Use environment variables, never hardcode secrets
- [ ] Implement firewall rules to restrict ARI access
- [ ] Enable database connection encryption
- [ ] Set up monitoring and alerting

### Reporting Security Issues

If you discover a security vulnerability, please **do not** open a public issue. Instead:
- Email: security@yourdomain.com
- Provide detailed steps to reproduce
- Allow 90 days for responsible disclosure

## 📖 API Documentation

Interactive API documentation is automatically generated by FastAPI.

### Swagger UI
- **URL:** `http://localhost:8000/docs`
- **Features:** Try out endpoints, view schemas, test authentication

### ReDoc
- **URL:** `http://localhost:8000/redoc`
- **Features:** Clean, printable documentation

### OpenAPI Schema
- **URL:** `http://localhost:8000/openapi.json`
- **Use:** Import into Postman, Insomnia, or other API clients

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. **Fork** the repository
2. **Create** a feature branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make** your changes following the code style
4. **Test** your changes:
   ```bash
   make test
   ```
5. **Commit** using conventional commits:
   ```bash
   git commit -m 'feat: add amazing feature'
   ```
6. **Push** to your fork:
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Open** a Pull Request

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

Pull requests are automatically tested via GitHub Actions.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/dny1020/api-contact-center/issues)
- **Discussions:** [GitHub Discussions](https://github.com/dny1020/api-contact-center/discussions)

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Asterisk](https://www.asterisk.org/) - Open-source communications platform
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL toolkit

---

**⭐ Star this repo if you find it useful!**

**Built with ❤️ for production telephony systems**
