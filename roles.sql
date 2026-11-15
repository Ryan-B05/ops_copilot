-- ============================================================
-- Ops Copilot: read only application role
--
-- Run as the postgres administrator after schema.sql.
-- The API connects as opscopilot_app, never as postgres.
-- Change the password before running.
-- ============================================================

CREATE ROLE opscopilot_app WITH LOGIN PASSWORD 'change_me';

GRANT CONNECT ON DATABASE opscopilot TO opscopilot_app;
GRANT USAGE ON SCHEMA public TO opscopilot_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO opscopilot_app;

-- no creating objects, and every transaction starts read only
REVOKE CREATE ON SCHEMA public FROM opscopilot_app;
ALTER ROLE opscopilot_app SET default_transaction_read_only = on;
