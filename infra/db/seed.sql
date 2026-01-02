-- SOLVER Database Seed Script
-- Extensions only - schema and seed data managed by Alembic

-- Enable required extensions for PostgreSQL
-- These run on Docker container initialization before Alembic
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- NOTE: Instance 0 seed data is in Alembic migration 001_initial_schema.py
-- Do NOT add seed data here to avoid duplicate key violations
