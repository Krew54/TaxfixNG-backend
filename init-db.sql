-- Initial database setup for TaxFix NG
-- This script runs automatically when PostgreSQL container starts

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- Set default search path
SET search_path TO public;

-- Initial database is created by POSTGRES_DB env variable
-- Additional initialization can be done here
