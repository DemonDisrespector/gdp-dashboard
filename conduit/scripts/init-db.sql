-- QuantumBridge database initialization
-- Runs once on first container start

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Audit schema (separate from application schema for access-control segregation)
CREATE SCHEMA IF NOT EXISTS audit;
COMMENT ON SCHEMA audit IS 'HIPAA §164.312(b) audit controls – restricted read access';

-- Grant minimal privileges
-- In production, create a dedicated audit_reader role with SELECT-only on audit.*
