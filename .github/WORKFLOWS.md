# GitHub Actions CI/CD Workflows

This repository includes automated CI/CD pipelines using GitHub Actions.

## Workflows

### 1. CI/CD Pipeline (`ci-cd.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Tags matching `v*` (e.g., v1.0.0)
- Pull requests to `main` or `develop`

**Jobs:**

#### Test
- Sets up Python 3.11
- Installs dependencies
- Runs pytest with coverage
- Uploads coverage to Codecov (optional)

#### Build and Push
- Builds Docker image for `linux/amd64` and `linux/arm64`
- Pushes to GitHub Container Registry (ghcr.io)
- Creates tags:
  - `main` → `latest`
  - `develop` → `develop`
  - `v1.2.3` → `1.2.3`, `1.2`, `1`, `latest`
  - Commits → `main-sha123abc`

#### Security Scan (main branch only)
- Scans Docker image with Trivy
- Uploads results to GitHub Security tab

### 2. Pull Request Checks (`pr-checks.yml`)

**Triggers:**
- Pull request opened, synchronized, or reopened

**Jobs:**

#### Validate
- Checks Python syntax
- Scans for secrets with TruffleHog

#### Test
- Runs full test suite

#### Build
- Builds Docker image (doesn't push)
- Validates Dockerfile

### 3. Release (`release.yml`)

**Triggers:**
- GitHub release published

**Jobs:**
- Builds multi-platform Docker image
- Pushes with version tags
- Updates release notes with Docker pull command

## Setup Instructions

### 1. Enable GitHub Container Registry

The workflows will automatically use GitHub Container Registry. No additional configuration needed.

### 2. Repository Settings

1. Go to repository **Settings** → **Actions** → **General**
2. Under "Workflow permissions", select:
   - ✅ **Read and write permissions**
   - ✅ **Allow GitHub Actions to create and approve pull requests**

### 3. Optional: Codecov Integration

To enable test coverage reports:

1. Sign up at [codecov.io](https://codecov.io)
2. Add your repository
3. Get the upload token
4. Add to repository secrets:
   - Name: `CODECOV_TOKEN`
   - Value: Your Codecov token

### 4. Branch Protection (Recommended)

Protect your `main` branch:

1. Go to **Settings** → **Branches**
2. Add rule for `main`
3. Enable:
   - ✅ Require pull request before merging
   - ✅ Require status checks to pass (select `Test` and `Build`)
   - ✅ Require branches to be up to date

## Using the Docker Images

### Pull from GitHub Container Registry

```bash
# Latest version
docker pull ghcr.io/YOUR_USERNAME/api_contact_center:latest

# Specific version
docker pull ghcr.io/YOUR_USERNAME/api_contact_center:1.2.3

# Develop branch
docker pull ghcr.io/YOUR_USERNAME/api_contact_center:develop
```

### Run the Container

```bash
docker run -d \
  --name contact-center-api \
  -p 8000:8000 \
  -e SECRET_KEY=your-secret \
  -e DATABASE_URL=postgresql://... \
  -e ARI_HTTP_URL=http://asterisk:8088/ari \
  -e ARI_USERNAME=ariuser \
  -e ARI_PASSWORD=aripass \
  ghcr.io/YOUR_USERNAME/api_contact_center:latest
```

### Use in docker-compose.yml

```yaml
services:
  api:
    image: ghcr.io/YOUR_USERNAME/api_contact_center:latest
    # ... rest of config
```

## Making a Release

### 1. Update Version

Update version in your code if needed.

### 2. Create and Push Tag

```bash
# Create tag
git tag -a v1.2.3 -m "Release version 1.2.3"

# Push tag
git push origin v1.2.3
```

### 3. Create GitHub Release

1. Go to **Releases** → **Draft a new release**
2. Select your tag (v1.2.3)
3. Add release notes
4. Click **Publish release**

The workflow will automatically:
- Build Docker images for amd64 and arm64
- Push to GitHub Container Registry
- Tag as `1.2.3`, `1.2`, `1`, and `latest`
- Add Docker pull command to release notes

## Workflow Status Badges

Add to your README.md:

```markdown
![CI/CD](https://github.com/YOUR_USERNAME/api_contact_center/workflows/CI%2FCD%20Pipeline/badge.svg)
![Tests](https://github.com/YOUR_USERNAME/api_contact_center/workflows/Pull%20Request%20Checks/badge.svg)
```

## Viewing Workflow Runs

1. Go to **Actions** tab in your repository
2. Click on any workflow run to see details
3. Check logs for each job

## Viewing Docker Images

1. Go to your repository main page
2. Click **Packages** on the right sidebar
3. View all published images and tags

## Troubleshooting

### Build Fails

Check the **Actions** tab for error logs. Common issues:
- Missing dependencies in requirements.txt
- Dockerfile errors
- Test failures

### Image Not Visible

Make sure the package is public:
1. Go to package settings
2. Change visibility to **Public**

### Permission Denied

Ensure repository settings allow workflow write permissions (see Setup step 2).

## Local Testing

Test the Docker build locally before pushing:

```bash
# Build image
docker build -t contact-center-api:test .

# Run tests in container
docker run --rm \
  -e DISABLE_DB=true \
  -e SECRET_KEY=test \
  contact-center-api:test \
  pytest tests/ -v
```

## Environment Variables for CI

The workflows use these environment variables during testing:

- `DISABLE_DB=true` - Run without database
- `SECRET_KEY=test-secret-key-for-ci-only` - Test JWT secret
- `ARI_HTTP_URL=http://test-asterisk:8088/ari` - Mock Asterisk URL
- `ARI_USERNAME=test` - Test credentials
- `ARI_PASSWORD=test` - Test credentials

## Security Scanning

Images pushed to `main` are automatically scanned with Trivy. View results in:
- **Security** tab → **Code scanning alerts**

## Cost Considerations

GitHub Actions usage:
- **Public repositories**: Free unlimited minutes
- **Private repositories**: 2,000 minutes/month free (Pro), 3,000 (Team)

GitHub Container Registry:
- **Public images**: Free unlimited storage
- **Private images**: 500MB free, then $0.25/GB/month

## Next Steps

1. Push code to GitHub
2. Workflows run automatically
3. View results in **Actions** tab
4. Pull Docker images from `ghcr.io`
5. Deploy to production!
