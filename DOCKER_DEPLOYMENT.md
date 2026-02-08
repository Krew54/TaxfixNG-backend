# TaxFix NG - Contabo Deployment with Docker Compose

## Overview
This setup provides a complete containerized deployment of TaxFix NG backend for Contabo VPS with:
- **PostgreSQL**: Database server running in a container
- **Redis**: In-memory cache and Celery message broker
- **FastAPI Application**: Main application server with local file storage
- **Celery Worker** (optional): For background tasks using Redis as broker

## Prerequisites

1. **Docker & Docker Compose** installed on your Contabo VPS
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   
   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **Git** (to clone the repository)
   ```bash
   sudo apt-get update
   sudo apt-get install -y git
   ```

## Deployment Steps

### 1. Clone and Setup the Repository
```bash
cd /opt/taxfix  # or your preferred directory
git clone https://github.com/Krew54/TaxfixNG-backend.git
cd TaxfixNG-backend
```

### 2. Configure Environment Variables
```bash
# Copy the .env file (it's already configured)
cp .env .env.production

# Edit .env.production to match your Contabo setup if needed
nano .env.production

# Key variables to review:
# - DB_PASSWORD: PostgreSQL password (strong password recommended)
# - JWT_SECRET_KEY: Ensure this is secure
# - STORAGE_PATH: Local storage path (default: /app/storage)
# - OPENAI_API_KEY & DEEPSEEK_API_KEY: Add your API keys if needed
```

### 3. Create Required Directories
```bash
# Create directories for persistent volumes
mkdir -p storage
mkdir -p postgres_data
mkdir -p redis_data

# Set appropriate permissions
chmod 755 storage
chmod 755 postgres_data
chmod 755 redis_data
```

### 4. Start the Containers

**For production deployment:**
```bash
# Use production compose file without auto-reload
docker-compose -f docker-compose.yml up -d
```

**For development/testing:**
```bash
# With live code reloading (slower, requires -d removed to see logs)
docker-compose up -d
```

### 5. Run Database Migrations
```bash
# Wait for containers to start (about 10 seconds)
sleep 10

# Run Alembic migrations
docker-compose exec app alembic upgrade head
```

### 6. Verify Deployment
```bash
# Check if all services are running
docker-compose ps

# Check logs
docker-compose logs -f app

# Test the API
curl http://localhost:8000/docs
```

## Key Features

### Local File Storage
- Documents are stored locally in the `storage/` directory instead of S3
- File structure: `storage/{user_email}/{unique_filename}`
- Files are accessible via `/api/documents/files/{user_email}/{filename}` endpoint
- Only authenticated users can access their own files

### Database Persistence
- PostgreSQL data persists in `postgres_data/` volume
- Database is automatically initialized from `.env` variables
- Alembic migrations are needed to set up tables

### Redis Setup
- Redis configured as Celery broker and cache backend
- Data persists in `redis_data/` volume
- Available at `redis:6379` within the Docker network

### Multi-Configuration
The setup supports:
- **Main App**: FastAPI application (port 8000)
- **Celery Worker**: Background job processing (optional, enabled by default)
- **PostgreSQL**: Database server (port 5432, internal access only)
- **Redis**: Cache/broker (port 6379, internal access only)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|------------|
| `/api/documents/upload` | POST | Upload a document with file |
| `/api/documents/` | GET | List all documents for current user |
| `/api/documents/{category}` | GET | List documents by category |
| `/api/documents/{doc_id}` | PUT | Update document metadata/file |
| `/api/documents/{doc_id}` | DELETE | Delete document |
| `/api/documents/files/{user_email}/{file_path}` | GET | Download document file |

## File Storage Structure

```
storage/
├── user1@example.com/
│   ├── 550e8400e29b41d4a716446655440000_invoice.pdf
│   └── 550e8400e29b41d4a716446655440001_receipt.jpg
├── user2@example.com/
│   └── 550e8400e29b41d4a716446655440002_tax_return.pdf
└── ...
```

## Important Notes

### Security Considerations
1. **Change Default Passwords**: Update `DB_PASSWORD`, `JWT_SECRET_KEY` in `.env.production`
2. **CORS Configuration**: Update `ALLOWED_ORIGINS` in docker-compose.yml if using custom domains
3. **File Permissions**: Storage files inherit the Docker container's user permissions
4. **Backup Strategy**: Regularly backup `postgres_data/` and `storage/` directories

### Scaling & Performance
- For high concurrency, consider adding multiple Celery workers
- Use a reverse proxy (nginx) in front of the app for production
- Consider adding health checks and monitoring

### Maintenance

#### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f postgres
docker-compose logs -f redis
```

#### Database Management
```bash
# Enter PostgreSQL shell
docker-compose exec postgres psql -U postgres -d taxfix

# Create a database backup
docker-compose exec postgres pg_dump -U postgres -d taxfix > backup.sql
```

#### File Storage Cleanup
```bash
# Clean up old files (ensure you have backups first)
# Manually delete files or implement cleanup logic in the app
ls -la storage/
```

#### Restart Services
```bash
# Restart specific service
docker-compose restart app

# Rebuild images after code changes
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### Stop All Services
```bash
docker-compose down

# With volume cleanup (careful - deletes data!)
docker-compose down -v
```

## Networking

The docker-compose setup creates an isolated network (`taxfix_network`) where services communicate using service names:
- App connects to PostgreSQL at `postgres:5432`
- App connects to Redis at `redis:6379`
- Celery worker uses the same configuration

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | PostgreSQL hostname | postgres |
| `DB_PORT` | PostgreSQL port | 5432 |
| `DB_USERNAME` | PostgreSQL user | postgres |
| `DB_PASSWORD` | PostgreSQL password | Password1$ |
| `DB_NAME` | Database name | taxfix |
| `STORAGE_PATH` | Local storage directory | /app/storage |
| `REDIS_HOST` | Redis hostname | redis |
| `REDIS_PORT` | Redis port | 6379 |
| `JWT_SECRET_KEY` | JWT signing key | (see .env) |
| `JWT_ALGORITHM` | JWT algorithm | HS256 |
| `OPENAI_API_KEY` | OpenAI API key | (configure as needed) |
| `DEEPSEEK_API_KEY` | DeepSeek API key | (configure as needed) |

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs app

# Common issues:
# 1. Port already in use: Change port mapping in docker-compose.yml
# 2. Insufficient disk space: Clean up old images with `docker prune`
# 3. Permission denied: Run with sudo or add user to docker group
```

### Database connection failed
```bash
# Ensure PostgreSQL is healthy
docker-compose ps postgres

# Check if database exists
docker-compose exec postgres psql -U postgres -l
```

### Alembic migration errors
```bash
# Run migrations manually
docker-compose exec app alembic upgrade head

# Check migration status
docker-compose exec app alembic current
```

### Files not persisting
```bash
# Verify volume mount
docker-compose exec app ls -la /app/storage

# Check disk space
docker-compose exec postgres df -h /var/lib/postgresql/data
```

## Production Checklist

- [ ] Update all passwords in `.env.production`
- [ ] Configure proper CORS origins
- [ ] Set up SSL/TLS with reverse proxy (nginx)
- [ ] Configure backup strategy for database and storage
- [ ] Set up monitoring and logging aggregation
- [ ] Configure firewall rules (only expose port 80/443)
- [ ] Set up automated backups with cron jobs
- [ ] Test disaster recovery procedures
- [ ] Document deployment for your team

## Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Celery Documentation](https://docs.celeryproject.io/)

## Support

For issues or questions about this deployment setup, refer to your repository documentation or contact your development team.
