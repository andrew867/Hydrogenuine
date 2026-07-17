CREATE EXTENSION IF NOT EXISTS vector;

-- Storage substrate tables are bootstrapped by StructuredDataStore.bootstrap_schema()
-- at runtime. This init script only ensures the vector extension is available.
-- All table creation is idempotent (CREATE IF NOT EXISTS) and handled in Python.
