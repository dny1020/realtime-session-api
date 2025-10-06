# CI/CD Setup Guide

This guide helps you set up GitHub Actions CI/CD for your Contact Center API.

## 🚀 Quick Setup (5 Minutes)

### Step 1: Push to GitHub

```bash
# Initialize git (if not done)
git init

# Add remote (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/api_contact_center.git

# Add all files
git add .

# Commit
git commit -m "Initial commit with CI/CD"

# Push to main
git push -u origin main
```

### Step 2: Enable GitHub Actions

GitHub Actions are automatically enabled for public repositories. For private repos:

1. Go to repository **Settings**
2. Click **Actions** → **General**
3. Under "Actions permissions", select **Allow all actions**
4. Click **Save**

### Step 3: Configure Repository Permissions

1. Go to **Settings** → **Actions** → **General**
2. Scroll to "Workflow permissions"
3. Select **Read and write permissions**
4. Check ✅ **Allow GitHub Actions to create and approve pull requests**
5. Click **Save**

### Step 4: That's It! 🎉

Your CI/CD pipeline is now active. Every push will:
- ✅ Run tests
- ✅ Build Docker images
- ✅ Push to GitHub Container Registry
- ✅ Scan for vulnerabilities

## 📦 Accessing Docker Images

### Make Package Public

By default, packages are private. To make them public:

1. Go to your repository main page
2. Click **Packages** on the right sidebar
3. Click on your package (`api_contact_center`)
4. Click **Package settings** (bottom right)
5. Scroll to "Danger Zone"
6. Click **Change visibility**
7. Select **Public**
8. Type the repository name to confirm
9. Click **I understand, change package visibility**

### Pull Your Image

```bash
# Replace YOUR_USERNAME with your GitHub username
docker pull ghcr.io/YOUR_USERNAME/api_contact_center:latest
```

## 🔄 Workflow Triggers

### Automatic Triggers

**CI/CD Pipeline** (`.github/workflows/ci-cd.yml`) runs on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Tags starting with `v` (e.g., v1.0.0)

**Pull Request Checks** (`.github/workflows/pr-checks.yml`) runs on:
- Pull request opened, updated, or reopened

**Release** (`.github/workflows/release.yml`) runs on:
- GitHub release published

### Manual Trigger

You can also run workflows manually:

1. Go to **Actions** tab
2. Select a workflow
3. Click **Run workflow**
4. Choose branch
5. Click **Run workflow**

## 📋 Creating Releases

### Method 1: Using GitHub UI

1. Go to repository **Releases**
2. Click **Draft a new release**
3. Click **Choose a tag**
4. Type new tag (e.g., `v1.0.0`)
5. Click **Create new tag**
6. Fill in release title and description
7. Click **Publish release**

### Method 2: Using Git Tags

```bash
# Create and push tag
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Then create release on GitHub UI
```

### What Happens

When you publish a release:
1. Release workflow builds Docker images
2. Images are tagged as:
   - `v1.0.0` (exact version)
   - `1.0` (major.minor)
   - `1` (major)
   - `latest` (if from main branch)
3. Multi-platform builds (amd64 + arm64)
4. Images pushed to GitHub Container Registry
5. Release notes updated with Docker pull command

## 🔍 Monitoring Workflows

### View Workflow Runs

1. Go to **Actions** tab
2. See all workflow runs with status
3. Click on any run to see details
4. Click on jobs to see logs

### Status Badges

Add to your README:

```markdown
![CI/CD](https://github.com/YOUR_USERNAME/api_contact_center/workflows/CI%2FCD%20Pipeline/badge.svg)
![Tests](https://github.com/YOUR_USERNAME/api_contact_center/workflows/Pull%20Request%20Checks/badge.svg)
```

## 🔒 Security Features

### Automated Security Scanning

Images pushed to `main` are scanned with Trivy. View results:

1. Go to **Security** tab
2. Click **Code scanning**
3. View alerts and details

### Secret Scanning

GitHub automatically scans for exposed secrets. If found:
- You'll receive an alert
- Workflow may fail
- Fix by removing secrets and rotating keys

### Dependabot

Automatically creates PRs for dependency updates:

1. Go to **Insights** → **Dependency graph**
2. Click **Dependabot**
3. Review and merge PRs

## 🎯 Using Docker Images in Production

### docker-compose.yml

```yaml
services:
  api:
    image: ghcr.io/YOUR_USERNAME/api_contact_center:latest
    # Or pin to specific version
    # image: ghcr.io/YOUR_USERNAME/api_contact_center:1.0.0
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=${DATABASE_URL}
      # ... other env vars
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: contact-center-api
spec:
  template:
    spec:
      containers:
      - name: api
        image: ghcr.io/YOUR_USERNAME/api_contact_center:1.0.0
        # ... rest of config
```

### Docker Run

```bash
docker run -d \
  --name contact-center-api \
  -p 8000:8000 \
  -e SECRET_KEY=your-secret \
  -e DATABASE_URL=postgresql://... \
  ghcr.io/YOUR_USERNAME/api_contact_center:latest
```

## 🛠️ Customizing Workflows

### Change Python Version

Edit `.github/workflows/ci-cd.yml`:

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.12'  # Change here
```

### Add More Tests

Edit workflow to add additional test commands:

```yaml
- name: Run tests
  run: |
    pytest tests/ -v
    pytest tests/ --cov=app  # Coverage
    mypy app/                # Type checking
    flake8 app/              # Linting
```

### Deploy to Cloud

Add deployment step after successful build:

```yaml
- name: Deploy to Cloud Run
  uses: google-github-actions/deploy-cloudrun@v1
  with:
    image: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
    service: contact-center-api
    region: us-central1
```

## 📊 Workflow Status

After setup, check:

1. ✅ Tests pass on every push
2. ✅ Docker images build successfully
3. ✅ Images appear in **Packages**
4. ✅ Security scans complete
5. ✅ Badges show passing status

## 🐛 Troubleshooting

### Workflow Fails

**Check logs:**
1. Go to **Actions**
2. Click failed run
3. Click failed job
4. Expand failed step
5. Read error message

**Common issues:**
- Missing dependencies: Update `requirements.txt`
- Test failures: Fix tests or code
- Docker build errors: Check Dockerfile
- Permission errors: Check repository settings (Step 3)

### Can't Pull Image

**Error: `unauthorized`**
- Package is private: Make it public (see Step 4)
- Not logged in: `docker login ghcr.io`

**Error: `not found`**
- Check package exists in **Packages**
- Verify username in image URL
- Check workflow completed successfully

### Security Scan Alerts

View in **Security** → **Code scanning**:
- Review vulnerability details
- Update dependencies if needed
- Suppress false positives if necessary

## 💡 Best Practices

1. **Always test locally first**
   ```bash
   pytest tests/ -v
   docker build -t test .
   ```

2. **Use semantic versioning**
   - v1.0.0 for releases
   - v1.0.1 for patches
   - v1.1.0 for features
   - v2.0.0 for breaking changes

3. **Pin production images**
   ```yaml
   # Good
   image: ghcr.io/user/app:1.2.3
   
   # Risky (auto-updates)
   image: ghcr.io/user/app:latest
   ```

4. **Review Dependabot PRs**
   - Check changelogs
   - Test locally
   - Merge regularly

5. **Monitor workflow costs**
   - Public repos: Free unlimited
   - Private repos: Check Actions usage in **Settings** → **Billing**

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Multi-platform Builds](https://docs.docker.com/build/building/multi-platform/)
- [Trivy Security Scanner](https://github.com/aquasecurity/trivy)

## ✅ Next Steps

1. ✅ Push code to GitHub
2. ✅ Enable Actions (auto-enabled)
3. ✅ Configure permissions
4. ✅ Make package public
5. ✅ Create first release
6. ✅ Pull and test Docker image
7. ✅ Deploy to production!

Your CI/CD pipeline is ready! 🚀
