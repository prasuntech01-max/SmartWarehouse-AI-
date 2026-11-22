-- Migration 002: Module 13 Benchmarking & Report Metadata Storage

CREATE TABLE IF NOT EXISTS benchmark_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    benchmark_name TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    environment_json TEXT NOT NULL,
    total_trials INTEGER NOT NULL,
    executed_by TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS benchmark_trials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    algorithm_name TEXT NOT NULL,
    scenario_seed INTEGER NOT NULL,
    num_robots INTEGER NOT NULL,
    grid_size TEXT NOT NULL,
    obstacle_density REAL NOT NULL,
    execution_time_ms REAL NOT NULL,
    memory_peak_kb REAL NOT NULL,
    path_length INTEGER NOT NULL,
    optimal_path_length INTEGER NOT NULL,
    optimality_ratio REAL NOT NULL,
    conflicts_detected INTEGER NOT NULL,
    replan_count INTEGER NOT NULL,
    success INTEGER NOT NULL,
    FOREIGN KEY(run_id) REFERENCES benchmark_runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS report_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    generated_by TEXT NOT NULL,
    time_range_start TIMESTAMP,
    time_range_end TIMESTAMP,
    summary_json TEXT NOT NULL,
    export_format TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bench_run ON benchmark_trials(run_id);
CREATE INDEX IF NOT EXISTS idx_report_time ON report_records(created_at);
