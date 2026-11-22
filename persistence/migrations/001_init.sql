-- Migration 001: initial schema for Module 12

CREATE TABLE IF NOT EXISTS migration_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash BLOB NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('ADMIN','OPERATOR','VIEWER')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP
);

-- Sessions table (optional persistence of tokens)
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    issued_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Incidents table (historical copy of hazard incidents)
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hazard_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    sensor_ids TEXT,
    device_id TEXT,
    coord_x INTEGER,
    coord_y INTEGER,
    value REAL,
    unit TEXT,
    tick INTEGER,
    rule_id TEXT,
    explanation TEXT,
    recovery TEXT,
    data_source TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Hazard audit log (append‑only with hash chain)
CREATE TABLE IF NOT EXISTS hazard_audits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('ACK','CLEAR','OVERRIDE')),
    username TEXT NOT NULL,
    tick INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    prev_hash TEXT,
    hash TEXT NOT NULL,
    FOREIGN KEY(incident_id) REFERENCES incidents(id)
);

-- Sensor readings (down‑sampled for history)
CREATE TABLE IF NOT EXISTS sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    tick INTEGER NOT NULL,
    data_source TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- System configuration key/value store
CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value TEXT
);
