-- Migration 003: Indexes, Audit Logs, and Operational Persistence (Additive & Non-Destructive)

CREATE INDEX IF NOT EXISTS idx_users_username_lower ON users(LOWER(username));
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_incidents_created ON incidents(created_at);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_sid_tick ON sensor_readings(sensor_id, tick);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT,
    status TEXT NOT NULL CHECK(status IN ('SUCCESS','FAILURE','WARNING')),
    details TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);

CREATE TABLE IF NOT EXISTS warehouse_tasks (
    task_id INTEGER PRIMARY KEY,
    pick_x INTEGER NOT NULL,
    pick_y INTEGER NOT NULL,
    drop_x INTEGER NOT NULL,
    drop_y INTEGER NOT NULL,
    priority INTEGER NOT NULL DEFAULT 2,
    status TEXT NOT NULL,
    assigned_robot INTEGER,
    created_at_step INTEGER NOT NULL DEFAULT 0,
    completed_at_step INTEGER,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS parcel_records (
    parcel_id TEXT PRIMARY KEY,
    parcel_type TEXT NOT NULL,
    rack_slot_id TEXT,
    status TEXT NOT NULL,
    location_x INTEGER,
    location_y INTEGER,
    dest_x INTEGER,
    dest_y INTEGER,
    assigned_robot INTEGER,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
