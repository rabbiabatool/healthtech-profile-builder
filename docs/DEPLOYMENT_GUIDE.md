# Deployment, Rollback & Disaster Recovery Guide (Week 6 Final Capstone)

## Overview
This guide provides complete instructions for local and production deployment of the containerized HealthTech learning platform, including database backups, zero-downtime rolling updates, and rollback procedures.

---

## 1. One-Command Local Startup (Docker Compose)

### Prerequisites
- Docker Engine 24.0+ & Docker Compose v2.20+
- Port availability: `8000` (Backend), `3000` (Frontend), `5432` (PostgreSQL)

### Quick Start
```bash
# 1. Clone repository and navigate to root
cd healthtech-profile-builder

# 2. Copy environment template
cp .env.example .env

# 3. Start the entire container stack
docker compose up --build -d

# 4. Verify running health checks
docker compose ps
```

Once running:
- **Next.js Web Portal**: [http://localhost:3000](http://localhost:3000)
- **API Swagger Documentation**: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- **Liveness Probe**: [http://localhost:8000/health](http://localhost:8000/health)
- **Readiness Probe**: [http://localhost:8000/ready](http://localhost:8000/ready)

Default Seed Credentials:
- **Member**: `member@healthtech.test` / `MemberPass123!`
- **Administrator**: `admin@healthtech.test` / `AdminPass123!`

---

## 2. Health & Readiness Monitoring

The platform exposes two standardized probes compatible with Docker and Kubernetes:

1. **Liveness Probe (`GET /health`)**:
   - Fast, non-blocking check verifying the Gunicorn/Django web worker is accepting traffic.
   - Status 200 returned in `< 5ms`.
2. **Readiness Probe (`GET /ready`)**:
   - Executes live SQL query on PostgreSQL (`SELECT 1`).
   - Verifies ML model artifact checksum and file integrity in `ml_artifacts/`.
   - Verifies active chunk count in `AdvancedHybridVectorStore`.
   - Returns 200 when ready, 503 if any dependency is degraded.

---

## 3. Database Backup & Disaster Recovery

### Creating a Timestamped PostgreSQL Backup
```bash
# Run pg_dump inside the database container
docker compose exec -T db pg_dump -U postgres -d healthtech_db -F c -b -v -f /tmp/backup_latest.dump

# Copy the backup dump to host storage
docker compose cp db:/tmp/backup_latest.dump ./backups/healthtech_db_$(date +%Y%m%d_%H%M%S).dump
```

### Restoring from Backup
```bash
# 1. Stop backend and worker containers to prevent active writes
docker compose stop backend worker

# 2. Drop existing connections and restore via pg_restore
docker compose exec -T db psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'healthtech_db';"
docker compose exec -T db pg_restore -U postgres -d healthtech_db --clean --if-exists -v /tmp/backup_latest.dump

# 3. Restart application containers
docker compose start backend worker
```

---

## 4. Zero-Downtime Deployment & Rollback Strategy

### Rolling Deployment Workflow
1. **Build New Images**:
   ```bash
   docker compose build backend worker frontend
   ```
2. **Run Database Migrations**:
   ```bash
   docker compose run --rm backend python manage.py migrate --noinput
   ```
3. **Graceful Container Reload**:
   ```bash
   docker compose up -d --no-deps backend frontend worker
   ```
4. **Automated Health Check Verification**:
   ```bash
   curl -f http://localhost:8000/ready || (echo "Deployment failed! Triggering rollback..." && exit 1)
   ```

### Rollback Procedure
If the readiness probe fails or regression tests detect an anomaly post-deploy:
```bash
# 1. Revert Git tag / commit to previous stable release
git checkout v5.0.0-phase4

# 2. Rebuild and launch previous container versions
docker compose up -d --build

# 3. If database schema was modified, restore pre-migration backup
./scripts/restore_db.sh ./backups/pre_deploy_backup.dump

# 4. Verify readiness
curl -f http://localhost:8000/ready
```
