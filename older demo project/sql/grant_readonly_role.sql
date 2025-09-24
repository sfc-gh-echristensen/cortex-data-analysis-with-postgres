-- SQL helper: create a read-only role and grant SELECT/USAGE privileges for demo objects
-- Run as an account admin or role with privilege to create roles and grant privileges.

-- Replace these names as needed
SET readonly_role = 'DEMO_READONLY_ROLE';
SET readonly_user = 'DEMO_READONLY_USER';
SET readonly_password = 'ChangeMe123!'; -- change to a secure value or create user externally

-- 1) Create role
CREATE ROLE IF NOT EXISTS IDENTIFIER($readonly_role);

-- 2) Grant usage on database and schema to role (run in your target DB/SCHEMA or set context first)
GRANT USAGE ON DATABASE CURRENT_DATABASE() TO ROLE IDENTIFIER($readonly_role);
GRANT USAGE ON SCHEMA CURRENT_SCHEMA() TO ROLE IDENTIFIER($readonly_role);

-- 3) Grant select on tables and views
GRANT SELECT ON ALL TABLES IN SCHEMA CURRENT_SCHEMA() TO ROLE IDENTIFIER($readonly_role);
GRANT SELECT ON ALL VIEWS IN SCHEMA CURRENT_SCHEMA() TO ROLE IDENTIFIER($readonly_role);

-- 4) Optionally create a user and assign the role (admin only)
-- CREATE USER IF NOT EXISTS IDENTIFIER($readonly_user) PASSWORD = $readonly_password DEFAULT_ROLE = IDENTIFIER($readonly_role) MUST_CHANGE_PASSWORD = FALSE;
-- GRANT ROLE IDENTIFIER($readonly_role) TO USER IDENTIFIER($readonly_user);

-- 5) Future grants (optional): ensure newly created objects are covered
ALTER DEFAULT PRIVILEGES IN SCHEMA CURRENT_SCHEMA() GRANT SELECT ON TABLES TO ROLE IDENTIFIER($readonly_role);

-- End of script
