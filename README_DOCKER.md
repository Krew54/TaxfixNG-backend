# TaxFix NG - Backend Application

A comprehensive tax filing and management application built with FastAPI, PostgreSQL, and Redis.

## Features

- **User Authentication**: Secure JWT-based authentication system
- **Document Management**: Upload, manage, and organize tax documents with local file storage
- **Tax Profiles**: Multi-profile support for different tax scenarios
- **Tax Blog**: Educational content and tax articles
- **Email Notifications**: Integration with MailJet for email communications
- **AI Integration**: OpenAI and DeepSeek API integration for intelligent tax assistance
- **Background Jobs**: Celery with Redis for asynchronous task processing
- **API Documentation**: Interactive Swagger and ReDoc documentation

## Tech Stack

- **Backend**: FastAPI with Python 3.11
- **Database**: PostgreSQL 16
- **Cache & Message Broker**: Redis 7
- **Task Queue**: Celery
- **Authentication**: JWT with bcrypt
- **File Storage**: Local filesystem (Contabo deployment) or AWS S3
- **Server**: Uvicorn ASGI

## Project Structure

```
TaxfixNG-backend/
│
├── app/
│   ├── runner.py                 # FastAPI app entry point
│   ├── worker.py                 # Celery worker configuration
│   ├── core/                     # App config, DB, settings, utils
│   │   ├── config.py             # Settings configuration
│   │   ├── database.py           # Database connection
│   │   ├── security.py           # JWT and security utilities
│   │   ├── storage.py            # Local file storage manager
│   │   └── utils.py              # General utilities
│   │
│   └── features/
│       ├── user/                 # User authentication and management
│       │   ├── user_auth.py
│       │   ├── user_models.py
│       │   ├── user_router.py
│       │   └── user_schema.py
│       │
│       ├── profile/              # User tax profiles
│       │   ├── profile_model.py
│       │   ├── profile_router.py
│       │   └── profile_schema.py
│       │
│       ├── doc_management/       # Document upload and management
│       │   ├── doc_models.py
│       │   ├── doc_router.py
│       │   └── doc_schemas.py
│       │
│       └── tax_article/          # Tax blog and articles
│           └── tax_blog_router.py
│
├── alembic/                      # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── docker-compose.yml            # Development Docker setup
├── docker-compose.prod.yml       # Production Docker setup
├── Dockerfile                    # Application container image
├── requirements.txt              # Python dependencies
├── alembic.ini                   # Database migration config
├── .env                          # Environment variables
├── .env.example                  # Environment template
├── deploy.sh                     # Linux/Mac deployment script
├── deploy.bat                    # Windows deployment script
├── DOCKER_DEPLOYMENT.md          # Detailed Docker deployment guide
├── init-db.sql                   # Database initialization
└── READme.md                     # Original project structure
```

## Quick Start - Development

### Prerequisites

- Python 3.11+
- PostgreSQL 12+
- Redis 6+
- pipenv or venv for virtual environment

### Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Krew54/TaxfixNG-backend.git
   cd TaxfixNG-backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Setup database**:
   ```bash
   alembic upgrade head
   ```

6. **Run the application**:
   ```bash
   python app/runner.py
   # Or with uvicorn directly:
   uvicorn app.runner:app --reload --host 0.0.0.0 --port 8000
   ```

The API will be available at `http://localhost:8000` with documentation at `http://localhost:8000/docs`.

## Docker Deployment - Contabo

This project includes comprehensive Docker support for easy deployment on Contabo or any Linux/Windows VPS.

### Quick Deploy

**For Linux/Mac**:
```bash
chmod +x deploy.sh
./deploy.sh
```

**For Windows**:
```bash
deploy.bat
```

### Manual Deploy

1. **Start all services**:
   ```bash
   # Development (with hot-reload)
   docker-compose up -d
   
   # Production (optimized)
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Run migrations**:
   ```bash
   docker-compose exec app alembic upgrade head
   ```

3. **View logs**:
   ```bash
   docker-compose logs -f app
   ```

### Services Included

- **PostgreSQL**: Primary database (port 5432, internal only)
- **Redis**: Cache and message broker (port 6379, internal only)
- **FastAPI App**: Main application (port 8000)
- **Celery Worker**: Background job processor (optional)

For detailed Docker deployment instructions, see [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md).

## API Endpoints

### User Management
- `POST /api/users/register` - Register new user
- `POST /api/users/login` - User login
- `GET /api/users/me` - Get current user profile
- `PUT /api/users/{user_id}` - Update user profile

### Profile Management
- `POST /api/profiles` - Create tax profile
- `GET /api/profiles` - List user profiles
- `GET /api/profiles/{profile_id}` - Get profile details
- `PUT /api/profiles/{profile_id}` - Update profile
- `DELETE /api/profiles/{profile_id}` - Delete profile

### Document Management  
- `POST /api/documents/upload` - Upload document
- `GET /api/documents` - List documents
- `GET /api/documents/{category}` - List documents by category
- `GET /api/documents/files/{user_email}/{file_path}` - Download document
- `PUT /api/documents/{doc_id}` - Update document
- `DELETE /api/documents/{doc_id}` - Delete document

### Content
- `GET /api/tax-articles` - List tax articles
- `GET /api/tax-articles/{article_id}` - Get article details

## Environment Variables

Key environment variables (see `.env.example` for all):

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=your_password
DB_NAME=taxfix

# Authentication
JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# File Storage (Local)
STORAGE_PATH=/app/storage

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# External APIs
OPENAI_API_KEY=your_key
DEEPSEEK_API_KEY=your_key
MAIL_JET_API_KEY=your_key
```

## Database Migrations

Using Alembic for schema management:

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## File Storage

Documents are stored locally in the configured `STORAGE_PATH`:

```
storage/
├── user1@example.com/
│   ├── uuid_filename1.pdf
│   └── uuid_filename2.jpg
└── user2@example.com/
    └── uuid_filename3.pdf
```

Files are organized by user email for security and easy management.

## Background Tasks

Celery workers handle async tasks like email sending:

```python
from celery import shared_task

@shared_task
def send_email_task(recipient, subject, body):
    # Email sending logic
    pass
```

Run worker locally:
```bash
celery -A app.worker worker --loglevel=info
```

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest

# With coverage
pytest --cov=app
```

## Security

- JWT-based authentication
- Password hashing with bcrypt
- SQL injection protection via SQLAlchemy ORM
- CORS configuration for API security
- Environment-based configuration for sensitive data
- File access restricted to authenticated users

## Performance Optimization

- Database connection pooling
- Redis caching for frequently accessed data
- Async/await for I/O operations
- Celery for background jobs
- Docker multi-stage builds for optimized images

## Troubleshooting

### Database connection issues
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U postgres -c "SELECT 1"
```

### Migration errors
```bash
# Check current migration
docker-compose exec app alembic current

# Rollback and reapply
docker-compose exec app alembic downgrade base
docker-compose exec app alembic upgrade head
```

### File upload issues
```bash
# Check storage directory
docker-compose exec app ls -la /app/storage/

# Check permissions
docker-compose exec app stat /app/storage/
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Test locally
4. Submit a pull request

## License

Proprietary - All rights reserved

## Support

For issues and support:
- GitHub Issues: [Project Issues](https://github.com/Krew54/TaxfixNG-backend/issues)
- Email: info@taxfixng.com
- Phone: 08033796049

## Version

- Current Version: 1.0
- Last Updated: 2026-02-08

---

**Note**: This application is now primarily deployed using Docker on Contabo VPS infrastructure. The migration from AWS to Contabo includes local file storage instead of S3, with data persisted in Docker volumes.
