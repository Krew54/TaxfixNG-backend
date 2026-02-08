# Migration Guide: AWS to Contabo with Docker

This guide documents the migration process from AWS infrastructure to Contabo VPS with Docker containerization.

## Overview of Changes

### Infrastructure Migration
- **From**: AWS RDS PostgreSQL + AWS S3 storage + EC2/distributed architecture
- **To**: Contabo VPS with containerized PostgreSQL, Redis, and local file storage

### Application Changes
- **File Storage**: S3 (boto3) → Local filesystem
- **Database**: AWS RDS → PostgreSQL in Docker container
- **Cache/Queue**: ElastiCache → Redis in Docker container
- **Deployment**: Manual EC2 configuration → Docker Compose

## Step-by-Step Migration

### Phase 1: Backup Existing Data

Before starting the migration, backup all critical data:

```bash
# Backup AWS RDS database
pg_dump -h taxfixng.c3kessyoyv4r.eu-north-1.rds.amazonaws.com \
        -U taxfixng \
        -d taxfixng > database_backup.sql

# Download S3 files
aws s3 cp s3://taxfix-docs/ ./s3_backup/ --recursive \
    --region us-east-1 \
    --profile default
```

### Phase 2: Update Application Code

✅ **Already Done**

1. Created new `app/core/storage.py` for local file storage
2. Updated `app/features/doc_management/doc_router.py` to use local storage instead of S3
3. Added `STORAGE_PATH` to `app/core/config.py`
4. Updated `.env` to remove AWS credentials and add local storage path

### Phase 3: Create Docker Infrastructure

✅ **Already Done**

1. Created `Dockerfile` for containerized application
2. Created `docker-compose.yml` for development environment
3. Created `docker-compose.prod.yml` for production environment
4. Created `init-db.sql` for database initialization
5. Created `.dockerignore` for optimized builds

### Phase 4: Setup Contabo VPS

```bash
# 1. SSH into your Contabo VPS
ssh root@your_contabo_ip

# 2. Update system
apt-get update && apt-get upgrade -y

# 3. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker root

# 4. Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 5. Install Git
apt-get install -y git

# 6. Clone repository
cd /opt/taxfix
git clone https://github.com/Krew54/TaxfixNG-backend.git
cd TaxfixNG-backend
```

### Phase 5: Configure Environment for Contabo

```bash
# 1. Create production .env file
cp .env.example .env.production

# 2. Edit configuration (update passwords, API keys, etc.)
nano .env.production

# Key changes in .env:
# - DB_HOST=postgres (Docker service name)
# - DB_USERNAME & DB_PASSWORD (secure values)
# - STORAGE_PATH=/app/storage
# - All AWS credentials removed
# - REDIS_HOST=redis (Docker service name)
```

### Phase 6: Database Migration

```bash
# 1. Start services
docker-compose -f docker-compose.prod.yml up -d

# 2. Wait for PostgreSQL to be ready
sleep 15

# 3. Restore database from AWS backup
docker-compose exec postgres psql -U postgres < database_backup.sql

# 4. Or, if first time, run migrations
docker-compose exec app alembic upgrade head
```

### Phase 7: Migrate File Storage

If you have existing files in S3, migrate them to local storage:

```bash
# 1. Create migration script
cat > migrate_s3_to_local.py << 'EOF'
import os
import boto3
from pathlib import Path

# AWS S3 configuration
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('AWS_SECRET_KEY'),
    region_name='us-east-1'
)

bucket = os.getenv('S3_BUCKET', 'taxfix-docs')
storage_path = Path('/app/storage')

# List all objects in S3
response = s3.list_objects_v2(Bucket=bucket)

for obj in response.get('Contents', []):
    key = obj['Key']
    
    # Create local directory structure
    local_path = storage_path / key
    local_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Download file
    s3.download_file(bucket, key, str(local_path))
    print(f"Downloaded: {key}")

print("Migration completed!")
EOF

# 2. Run migration (from your local machine)
export AWS_ACCESS_KEY=your_key
export AWS_SECRET_KEY=your_secret
python migrate_s3_to_local.py

# 3. Or, manually upload files to Docker volume
# Copy files to container
docker cp s3_backup/ taxfix_app:/app/storage/restore/
```

### Phase 8: DNS and Reverse Proxy Setup

```bash
# 1. Update DNS records to point to Contabo IP
# In your domain provider, update A record to point to Contabo IP

# 2. Setup Nginx as reverse proxy (recommended)
apt-get install -y nginx certbot python3-certbot-nginx

# 3. Create Nginx config
cat > /etc/nginx/sites-available/taxfix << 'EOF'
server {
    listen 80;
    server_name api.taxfixng.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Serve files directly from storage volume
    location /storage/ {
        alias /app/storage/;
        expires 7d;
    }
}
EOF

# 4. Enable site and test
ln -s /etc/nginx/sites-available/taxfix /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# 5. Setup SSL with Let's Encrypt
certbot --nginx -d api.taxfixng.com
```

### Phase 9: Backup and Monitoring Setup

```bash
# 1. Create backup script
cat > /opt/taxfix/backup.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/opt/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec -T postgres pg_dump -U postgres -d taxfix | \
    gzip > $BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz

# Backup storage volume
tar -czf $BACKUP_DIR/storage_backup_$TIMESTAMP.tar.gz /opt/taxfix/storage/

# Keep only last 7 days of backups
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +7 -delete
find $BACKUP_DIR -name "storage_backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed at $(date)"
EOF

chmod +x /opt/taxfix/backup.sh

# 2. Add to crontab for daily backups
crontab -e
# Add line: 0 2 * * * /opt/taxfix/backup.sh >> /var/log/taxfix_backup.log 2>&1
```

### Phase 10: Testing and Validation

```bash
# 1. Check service status
docker-compose ps

# 2. Test API
curl http://your_contabo_ip:8000/docs

# 3. Test database connection
docker-compose exec app python -c "from app.core.database import SessionLocal; db = SessionLocal(); print('DB Connected!')"

# 4. Test file upload endpoint
# Use your API client to upload a test document

# 5. Test file retrieval
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://your_contabo_ip:8000/api/documents/files/test@example.com/test_file.pdf
```

## Important Notes

### S3 to Local Storage Mapping

The old S3 URLs format:
```
https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}
Example: https://taxfix-docs.s3.us-east-1.amazonaws.com/documents/user@example.com/file.pdf
```

New local storage URL format:
```
/api/documents/files/{user_email}/{filename}
Example: /api/documents/files/user@example.com/uuid_file.pdf
```

### Database Structure

The database structure remains the same. The `file_url` column in the documents table now stores:
- **Old**: `https://taxfix-docs.s3.us-east-1.amazonaws.com/documents/...`
- **New**: `/api/documents/files/user@example.com/uuid_file.pdf`

You can update existing records:
```sql
UPDATE documents 
SET file_url = REPLACE(
    file_url, 
    'https://taxfix-docs.s3.us-east-1.amazonaws.com/', 
    '/api/documents/files/'
)
WHERE file_url LIKE 'https://taxfix-docs.s3%';
```

## Rollback Plan

If you need to rollback to AWS:

1. **Keep AWS resources active** during the transition period
2. **Update DNS TTL** to 5 minutes for quick rollback
3. **Use secondary DNS** pointing back to AWS as fallback
4. **Monitor logs** for issues during migration
5. **Have database dump ready** for quick restoration

## Post-Migration Checklist

- [ ] All services running (`docker-compose ps`)
- [ ] Database accessible and migrated
- [ ] Files migrated from S3 to local storage
- [ ] API endpoints responding correctly
- [ ] Document upload/download working
- [ ] Authentication working with JWT
- [ ] CORS configured for frontend domains
- [ ] SSL certificate setup and renewing
- [ ] Backup script running daily
- [ ] Monitoring and alerting configured
- [ ] Database indexed for performance
- [ ] Log aggregation setup (optional but recommended)
- [ ] Health checks enabled
- [ ] Rate limiting configured (optional)

## Performance Considerations

### Resource Allocation on Contabo

Recommended specs:
- **CPU**: 4+ cores
- **RAM**: 8GB+ (for PostgreSQL cache)
- **Disk**: 100GB+ (for database + storage)
- **Bandwidth**: Unlimited preferred

### Optimization Tips

1. **Database**:
   ```sql
   -- Add indexes for common queries
   CREATE INDEX idx_documents_user_email ON documents(user_email);
   CREATE INDEX idx_documents_user_category ON documents(user_email, category);
   ```

2. **Redis** (cache frequently accessed data):
   ```python
   # Implement caching for user profiles, etc.
   ```

3. **App** (use connection pooling):
   - Already configured in docker-compose

## Support & Troubleshooting

### Common Issues

**Issue**: Pod fails to start with "Connection refused"
```bash
# Solution: Wait longer for PostgreSQL to be ready
docker-compose logs postgres
docker-compose exec postgres pg_isready
```

**Issue**: Out of disk space
```bash
# Solution: Cleanup old Docker layers
docker system prune -a --volumes
```

**Issue**: Files not accessible
```bash
# Solution: Check permissions
docker-compose exec app ls -la /app/storage/
chmod -R 755 /app/storage/
```

## Contact & Support

- Repository: https://github.com/Krew54/TaxfixNG-backend
- Email: info@taxfixng.com
- Support: 08033796049

---

**Migration Date**: 2026-02-08  
**Final Status**: ✅ Successfully migrated from AWS to Contabo
