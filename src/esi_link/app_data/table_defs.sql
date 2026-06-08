-- Table definitions for the Esi-Link app-data SQLite database.
-- Columns that store JSON data are defined as BLOB to allow for efficient storage and retrieval.
-- timestamps are stored as nanosecond integers unless otherwise noted.

-- The OauthMetadataCache table stores cached OAuth metadata for ESI.
-- This is designed to support a single entry.
CREATE TABLE IF NOT EXISTS OauthMetadataCache (
    ID INTEGER PRIMARY KEY CHECK (ID=0),
    timestamped INTEGER NOT NULL,
    metadata_json BLOB NOT NULL
);

-- The SchemaCache table stores cached ESI schema data.
-- This table is designed to support multiple schemas, but only one per compatibility date.
CREATE TABLE IF NOT EXISTS SchemaCache (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamped INTEGER NOT NULL,
    compatibility_date TEXT NOT NULL UNIQUE,
    schema_json BLOB NOT NULL
);

-- The CompatibilityDatesCache table stores cached compatibility dates for ESI.
-- This is designed to support a single entry.
CREATE TABLE IF NOT EXISTS CompatibilityDatesCache (
    ID INTEGER PRIMARY KEY CHECK (ID=0),
    timestamped INTEGER NOT NULL,
    compatibility_dates_json BLOB NOT NULL
);

-- The Credentials table stores the app's ESI credentials and related information.
-- At the moment, this is designed to support a single set of credentials, 
-- but multiple sets of credentials could be supported in the future.
CREATE TABLE IF NOT EXISTS Credentials (
    ID INTEGER PRIMARY KEY CHECK (ID=0),
    app_name TEXT NOT NULL,
    app_description TEXT NOT NULL,
    client_id TEXT NOT NULL,
    client_secret TEXT NOT NULL,
    callback_url TEXT NOT NULL,
    scopes_json BLOB NOT NULL,
    timestamped INTEGER NOT NULL
);

-- The CharacterTokens table stores access and refresh tokens for ESI characters.
-- expires_at is stored as a Unix timestamp in seconds.
-- If multiple sets of credentials are supported in the future, 
--   this table may need to be updated to associate tokens with specific credentials.
CREATE TABLE IF NOT EXISTS CharacterTokens (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL UNIQUE,
    character_name TEXT NOT NULL,
    oauth_token_json BLOB NOT NULL,
    expires_at INTEGER NOT NULL,
    timestamped INTEGER NOT NULL
);