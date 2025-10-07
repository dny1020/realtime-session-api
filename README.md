# Contact Center API

![CI/CD](https://github.com/YOUR_USERNAME/api_contact_center/workflows/CI%2FCD%20Pipeline/badge.svg)
![Tests](https://github.com/YOUR_USERNAME/api_contact_center/workflows/Pull%20Request%20Checks/badge.svg)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Production-ready FastAPI service for **single outbound IVR calls** via Asterisk ARI with real-time WebSocket status updates.

## Features

- 🎯 Single call origination to specific numbers
- 📊 Real-time status updates via WebSocket
- 🔐 JWT authentication with bcrypt
- 🗄️ PostgreSQL persistence
- 🐳 Docker ready with multi-platform images
- 🚀 CI/CD with GitHub Actions
- 📝 RESTful API with OpenAPI docs

## Quick Start

### Using Makefile (Recommended)

```bash
# Complete first-time setup (creates .env, starts services, runs migrations, creates user)
make quick-start

# Daily commands
make up          # Start services
make logs        # View logs
make test        # Run tests
make health      # Check API health
make down        # Stop services

# See all commands
make help
```

See [MAKEFILE_GUIDE.md](MAKEFILE_GUIDE.md) for complete command reference.

### Using Docker Compose (Manual)

```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/YOUR_USERNAME/api_contact_center:latest

# Or use docker-compose
docker-compose up -d
```

See [QUICKSTART.md](QUICKSTART.md) for detailed manual setup.

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v2/token` | Get JWT token | No |
| POST | `/api/v2/interaction/{number}` | Originate call | Yes |
| GET | `/api/v2/status/{call_id}` | Get call status | Yes |
| POST | `/api/v2/calls` | Create call (RESTful) | Yes |
| GET | `/api/v2/calls/{call_id}` | Get call details | Yes |
| GET | `/health` | Health check | No |
| GET | `/docs` | API documentation | No |

## Usage Example

```bash
# Get token
curl -X POST http://localhost:8000/api/v2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=yourpass"

# Make call
TOKEN="your_token"
curl -X POST http://localhost:8000/api/v2/interaction/+1234567890 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"context":"outbound-ivr","caller_id":"MyCompany"}'

# Check status (updates in real-time!)
curl -X GET http://localhost:8000/api/v2/status/{call_id} \
  -H "Authorization: Bearer $TOKEN"
```

## Architecture

```
Client → FastAPI API ← PostgreSQL
            ↓
        Asterisk (WebSocket + HTTP)
```

**Call Status Flow:**  
`pending` → `dialing` → `ringing` → `answered` → `completed`

Status updates automatically via WebSocket events from Asterisk.

## Docker Images

Available on GitHub Container Registry:

```bash
# Latest
docker pull ghcr.io/YOUR_USERNAME/api_contact_center:latest

# Specific version
docker pull ghcr.io/YOUR_USERNAME/api_contact_center:1.0.0

# Development
docker pull ghcr.io/YOUR_USERNAME/api_contact_center:develop
```

**Multi-platform support:** `linux/amd64` and `linux/arm64`

## Configuration

Key environment variables (see [.env.example](.env.example)):

```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Asterisk ARI (external service)
ARI_HTTP_URL=http://asterisk-server:8088/ari
ARI_USERNAME=ariuser
ARI_PASSWORD=secure_password
ARI_APP=contactcenter

# Security
SECRET_KEY=your-strong-secret-key
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start locally
uvicorn app.main:app --reload
```

Tests run automatically on push via GitHub Actions.

## CI/CD Pipeline

Automated workflows for:
- ✅ Testing on every push
- ✅ Multi-platform Docker builds
- ✅ Publishing to GitHub Container Registry
- ✅ Security scanning with Trivy
- ✅ Dependency updates with Dependabot

See [CI_CD_SETUP.md](CI_CD_SETUP.md) for setup instructions.

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
- **[PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)** - Production deployment guide
- **[CI_CD_SETUP.md](CI_CD_SETUP.md)** - CI/CD setup and usage
- **[CHANGES_SUMMARY.md](CHANGES_SUMMARY.md)** - Recent changes and features
- **[TEST_RESULTS.md](TEST_RESULTS.md)** - Test execution details

## Tech Stack

- Python 3.11+ / FastAPI 0.117+
- PostgreSQL 15 / SQLAlchemy 2.0 / Alembic
- Asterisk ARI (WebSocket + HTTP)
- JWT (python-jose) / Bcrypt (passlib)
- Docker / GitHub Actions

## Security

- ✅ JWT authentication with bcrypt hashing
- ✅ Rate limiting (10 req/60s on token endpoint)
- ✅ Input validation with Pydantic
- ✅ SQL injection protection (ORM)
- ✅ Non-root Docker user
- ✅ Automated security scanning
- ✅ No public Asterisk ARI exposure

## API Documentation

Interactive docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/name`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push to branch (`git push origin feature/name`)
5. Open Pull Request

PRs are automatically tested via GitHub Actions.

## License

[MIT License](LICENSE)

## Support

- **Issues:** [GitHub Issues](https://github.com/YOUR_USERNAME/api_contact_center/issues)
- **Discussions:** [GitHub Discussions](https://github.com/YOUR_USERNAME/api_contact_center/discussions)

---

⭐ **Star this repo if you find it useful!**
