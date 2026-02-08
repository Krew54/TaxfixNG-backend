#!/bin/bash

# TaxFix NG - Docker Deployment Script
# This script automates the deployment process on Contabo or any server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  TaxFix NG - Docker Deployment Script  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed!${NC}"
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo -e "${GREEN}✓ Docker installed${NC}"
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed!${NC}"
    echo "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✓ Docker Compose installed${NC}"
fi

# Verify Docker versions
echo ""
echo "Docker version:"
docker --version
echo "Docker Compose version:"
docker-compose --version
echo ""

# Ask for deployment type
echo -e "${YELLOW}Select deployment type:${NC}"
echo "1) Development (with hot-reload)"
echo "2) Production (optimized)"
read -p "Enter choice [1-2]: " DEPLOY_TYPE

case $DEPLOY_TYPE in
    1)
        COMPOSE_FILE="docker-compose.yml"
        MODE="Development"
        ;;
    2)
        COMPOSE_FILE="docker-compose.prod.yml"
        MODE="Production"
        ;;
    *)
        echo -e "${RED}Invalid choice!${NC}"
        exit 1
        ;;
esac

echo -e "${YELLOW}Deployment mode: $MODE${NC}"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env file not found!${NC}"
    read -p "Do you want to create it from .env.example? (y/n): " CREATE_ENV
    if [ "$CREATE_ENV" = "y" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env file${NC}"
        echo -e "${YELLOW}⚠ Please edit .env with your configuration${NC}"
        read -p "Continue after editing .env? (y/n): " CONTINUE
        if [ "$CONTINUE" != "y" ]; then
            exit 1
        fi
    else
        echo -e "${RED}✗ .env file is required!${NC}"
        exit 1
    fi
fi

# Create directories for volumes
echo ""
echo "Creating directories for persistent volumes..."
mkdir -p storage
mkdir -p postgres_data
mkdir -p redis_data
chmod 755 storage postgres_data redis_data
echo -e "${GREEN}✓ Directories created${NC}"

# Build images
echo ""
echo -e "${YELLOW}Building Docker images...${NC}"
docker-compose -f $COMPOSE_FILE build

# Start services
echo ""
echo -e "${YELLOW}Starting services...${NC}"
docker-compose -f $COMPOSE_FILE up -d

# Wait for services to be healthy
echo ""
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
sleep 10

# Check service health
echo ""
echo "Service status:"
docker-compose -f $COMPOSE_FILE ps

# Run migrations
echo ""
echo -e "${YELLOW}Running database migrations...${NC}"
docker-compose -f $COMPOSE_FILE exec -T app alembic upgrade head

# Display summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Deployment Completed Successfully!   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}API available at:${NC} http://localhost:8000"
echo -e "${GREEN}API Docs:${NC} http://localhost:8000/docs"
echo ""
echo "Useful commands:"
echo "  View logs:              docker-compose -f $COMPOSE_FILE logs -f app"
echo "  Restart services:       docker-compose -f $COMPOSE_FILE restart"
echo "  Stop services:          docker-compose -f $COMPOSE_FILE down"
echo "  Clean up everything:    docker-compose -f $COMPOSE_FILE down -v"
echo ""

# Ask to show logs
read -p "Show application logs now? (y/n): " SHOW_LOGS
if [ "$SHOW_LOGS" = "y" ]; then
    docker-compose -f $COMPOSE_FILE logs -f app
fi
