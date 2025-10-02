# Pre-Deployment Checklist

Use this checklist before deploying to production.

## ✅ Configuration

- [ ] `.env` file created from `.env.example`
- [ ] `SECRET_KEY` generated (64 hex characters minimum)
- [ ] `POSTGRES_PASSWORD` changed from default
- [ ] `ARI_PASSWORD` changed from default
- [ ] `GF_SECURITY_ADMIN_PASSWORD` set to strong password
- [ ] `API_HOST` set to your domain
- [ ] `ACME_EMAIL` set to valid email
- [ ] `DEBUG=false` in production
- [ ] `DOCS_ENABLED=false` in production
- [ ] `ALLOWED_ORIGINS` restricted to known domains
- [ ] `DATABASE_URL` properly configured
- [ ] `ARI_HTTP_URL` points to Asterisk server
- [ ] `WORKERS` set based on CPU cores

## ✅ Infrastructure

- [ ] VPS meets minimum requirements (2GB RAM, 2 CPU cores)
- [ ] Docker and Docker Compose installed
- [ ] Domain name registered
- [ ] DNS A records configured
- [ ] Firewall configured (ports 22, 80, 443)
- [ ] SSH key authentication enabled
- [ ] Non-root user created
- [ ] Adequate disk space (20GB+ available)

## ✅ Asterisk

- [ ] Asterisk server accessible
- [ ] ARI enabled in `ari.conf`
- [ ] HTTP enabled in `http.conf`
- [ ] ARI credentials configured
- [ ] Stasis application created
- [ ] SIP trunk configured
- [ ] Dialplan context created
- [ ] Test call successful

## ✅ Security

- [ ] All default passwords changed
- [ ] SSH password authentication disabled
- [ ] Firewall enabled and configured
- [ ] SSL/TLS via Let's Encrypt configured
- [ ] Security headers enabled (via Traefik)
- [ ] Rate limiting configured
- [ ] CORS origins restricted
- [ ] OpenAPI docs disabled in production
- [ ] Database not exposed externally
- [ ] Prometheus/Grafana not exposed (or protected)

## ✅ Database

- [ ] PostgreSQL running and healthy
- [ ] Database migrations completed
- [ ] First admin user created
- [ ] Database backup strategy defined
- [ ] Backup restoration tested
- [ ] Connection pooling configured

## ✅ Monitoring

- [ ] Prometheus collecting metrics
- [ ] Grafana configured (if used)
- [ ] Alert rules loaded
- [ ] Health check endpoint responding
- [ ] Logs are accessible
- [ ] Log rotation configured
- [ ] Metrics retention policy set

## ✅ Testing

- [ ] Health endpoint returns 200
- [ ] Authentication endpoint works
- [ ] Test call originated successfully
- [ ] Call status retrieval works
- [ ] Metrics endpoint accessible
- [ ] SSL certificate valid
- [ ] HTTPS redirect working
- [ ] Rate limiting tested
- [ ] Load testing completed (optional)

## ✅ Backup & Recovery

- [ ] Database backup script created
- [ ] Automated backups scheduled (cron)
- [ ] Backup restoration procedure documented
- [ ] Configuration files backed up
- [ ] Recovery procedure tested

## ✅ Documentation

- [ ] Team trained on deployment
- [ ] Troubleshooting guide reviewed
- [ ] API documentation accessible to team
- [ ] Runbook created for common issues
- [ ] Contact information for emergencies
- [ ] Monitoring dashboards explained

## ✅ Post-Deployment

- [ ] Monitor logs for first 24 hours
- [ ] Verify no errors in logs
- [ ] Check resource usage (CPU, RAM, disk)
- [ ] Verify SSL certificate auto-renewal works
- [ ] Test failover scenarios
- [ ] Document any issues encountered
- [ ] Update team on deployment status

## 🔴 Red Flags (DO NOT DEPLOY IF TRUE)

- [ ] Using default `SECRET_KEY`
- [ ] Using default passwords
- [ ] `DEBUG=true` in production
- [ ] Database exposed to public
- [ ] No backups configured
- [ ] SSL certificate not working
- [ ] Health check failing
- [ ] Cannot connect to Asterisk
- [ ] Critical errors in logs
- [ ] Insufficient VPS resources

## 📝 Deployment Command

Once all items are checked:

```bash
# Clone repository
git clone https://github.com/dny1020/api-contact-center.git
cd api-contact-center

# Configure environment
cp .env.example .env
vim .env  # Update all values

# Start database
docker-compose up -d postgres
sleep 10

# Run migrations
docker-compose run --rm api alembic upgrade head

# Create admin user
docker-compose run --rm api python -m app.auth.create_user

# Start all services
docker-compose up -d

# Verify deployment
curl https://api.yourdomain.com/health
```

## 🎯 Success Criteria

Deployment is successful when:
- ✅ All services are running (`docker-compose ps` shows all healthy)
- ✅ Health endpoint returns 200 with all services "ok"
- ✅ HTTPS is working with valid certificate
- ✅ Authentication works
- ✅ Test call completes successfully
- ✅ No errors in logs
- ✅ Monitoring is collecting data

## 📞 Emergency Contacts

**Before deployment, fill in:**

| Role | Name | Contact |
|------|------|---------|
| DevOps Lead | | |
| SysAdmin | | |
| Asterisk Admin | | |
| Project Manager | | |
| On-Call Engineer | | |

## 📅 Maintenance Windows

Schedule regular maintenance:
- **Weekly**: Log review, disk space check
- **Monthly**: Security updates, backup verification
- **Quarterly**: Load testing, disaster recovery drill
- **Yearly**: Certificate renewal (automatic), major updates

---

**Sign-off:**

- [ ] Deployment lead approves: _________________ Date: _______
- [ ] Security review complete: _________________ Date: _______
- [ ] Final testing passed: _____________________ Date: _______

**Deployment Date:** __________________
**Deployed By:** ______________________
**Version:** __________________________
