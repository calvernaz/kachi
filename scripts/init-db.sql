-- Kachi Database Initialization Script
-- This script sets up the initial database configuration for Kachi

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create application user (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'kachi_app') THEN
        CREATE ROLE kachi_app WITH LOGIN PASSWORD 'kachi_app_password';
    END IF;
END
$$;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE kachi TO kachi_app;
GRANT USAGE ON SCHEMA public TO kachi_app;
GRANT CREATE ON SCHEMA public TO kachi_app;

-- Create indexes for performance (these will be created by Alembic migrations)
-- This is just for reference and optimization

-- Performance monitoring view
CREATE OR REPLACE VIEW performance_stats AS
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY tablename, attname;

-- Grant access to performance stats
GRANT SELECT ON performance_stats TO kachi_app;

-- Set up connection limits
ALTER ROLE kachi_app CONNECTION LIMIT 50;

-- Configure default settings for the application user
ALTER ROLE kachi_app SET statement_timeout = '30s';
ALTER ROLE kachi_app SET lock_timeout = '10s';
ALTER ROLE kachi_app SET idle_in_transaction_session_timeout = '60s';

-- Log successful initialization
INSERT INTO pg_stat_statements_info (dealloc) VALUES (0) ON CONFLICT DO NOTHING;
