@echo off
REM TaxFix NG - Windows Docker Deployment Script
REM This script automates the deployment process on Windows

setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════╗
echo ║  TaxFix NG - Docker Deployment Script  ║
echo ║                Windows                 ║
echo ╚════════════════════════════════════════╝
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker is not installed!
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo Docker is installed:
docker --version
echo.

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker Compose is not installed!
    echo Please ensure Docker Desktop is fully installed with Compose support
    pause
    exit /b 1
)

echo Docker Compose is installed:
docker-compose --version
echo.

REM Ask for deployment type
echo Select deployment type:
echo 1) Development (with hot-reload)
echo 2) Production (optimized)
set /p DEPLOY_TYPE="Enter choice [1-2]: "

if "%DEPLOY_TYPE%"=="1" (
    set COMPOSE_FILE=docker-compose.yml
    set MODE=Development
) else if "%DEPLOY_TYPE%"=="2" (
    set COMPOSE_FILE=docker-compose.prod.yml
    set MODE=Production
) else (
    echo Invalid choice!
    pause
    exit /b 1
)

echo Deployment mode: %MODE%
echo.

REM Check if .env file exists
if not exist ".env" (
    echo .env file not found!
    set /p CREATE_ENV="Do you want to create it from .env.example [y/n]: "
    if "!CREATE_ENV!"=="y" (
        if exist ".env.example" (
            copy .env.example .env
            echo Created .env file
            echo Please edit .env with your configuration
            pause
        ) else (
            echo .env.example not found!
            pause
            exit /b 1
        )
    ) else (
        echo .env file is required!
        pause
        exit /b 1
    )
)

REM Create directories for volumes
echo.
echo Creating directories for persistent volumes...
if not exist "storage" mkdir storage
if not exist "postgres_data" mkdir postgres_data
if not exist "redis_data" mkdir redis_data
echo Directories created
echo.

REM Build images
echo Building Docker images...
docker-compose -f %COMPOSE_FILE% build
if %errorlevel% neq 0 (
    echo Build failed!
    pause
    exit /b 1
)

REM Start services
echo.
echo Starting services...
docker-compose -f %COMPOSE_FILE% up -d

REM Wait for services
echo.
echo Waiting for services to be healthy...
timeout /t 10

REM Check service status
echo.
echo Service status:
docker-compose -f %COMPOSE_FILE% ps
echo.

REM Run migrations
echo Running database migrations...
docker-compose -f %COMPOSE_FILE% exec -T app alembic upgrade head
echo.

REM Display summary
echo.
echo ╔════════════════════════════════════════╗
echo ║  Deployment Completed Successfully!   ║
echo ╚════════════════════════════════════════╝
echo.
echo API available at: http://localhost:8000
echo API Docs:         http://localhost:8000/docs
echo.
echo Useful commands:
echo   View logs:              docker-compose -f %COMPOSE_FILE% logs -f app
echo   Restart services:       docker-compose -f %COMPOSE_FILE% restart
echo   Stop services:          docker-compose -f %COMPOSE_FILE% down
echo   Clean up everything:    docker-compose -f %COMPOSE_FILE% down -v
echo.

set /p SHOW_LOGS="Show application logs now [y/n]: "
if "%SHOW_LOGS%"=="y" (
    docker-compose -f %COMPOSE_FILE% logs -f app
)

pause
