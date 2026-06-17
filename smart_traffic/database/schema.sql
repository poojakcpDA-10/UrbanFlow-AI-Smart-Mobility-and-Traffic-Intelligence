-- SmartTraffic AI — Database Schema Reference
-- Engine: SQLite (dev) / PostgreSQL (prod)
-- ORM: Flask-SQLAlchemy

-- ──────────────────────────────────────────
-- USERS (roles: admin | supervisor | operator)
-- ──────────────────────────────────────────
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'operator',  -- admin | supervisor | operator
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    reset_token VARCHAR(255),
    reset_token_expiry DATETIME,
    assigned_intersection VARCHAR(50)
);

-- Role-based login redirects:
--   admin      → /admin/dashboard
--   supervisor → /supervisor/monitoring
--   operator   → /operator/cameras

-- ──────────────────────────────────────────
-- CAMERAS
-- ──────────────────────────────────────────
CREATE TABLE cameras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id VARCHAR(50) UNIQUE,        -- CAM-001, CAM-002...
    name VARCHAR(100),
    intersection_id VARCHAR(50),
    location_name VARCHAR(200),
    lat FLOAT,
    lng FLOAT,
    stream_url VARCHAR(255),             -- RTSP URL or webcam index
    is_active BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'online', -- online | offline | maintenance
    resolution VARCHAR(20) DEFAULT '1080p',
    fps INTEGER DEFAULT 30,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ──────────────────────────────────────────
-- DETECTIONS (ViT output per frame)
-- ──────────────────────────────────────────
CREATE TABLE detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    intersection_id VARCHAR(50),
    camera_id VARCHAR(50),
    vehicle_count INTEGER DEFAULT 0,
    cars INTEGER DEFAULT 0,
    buses INTEGER DEFAULT 0,
    trucks INTEGER DEFAULT 0,
    bikes INTEGER DEFAULT 0,
    emergency INTEGER DEFAULT 0,
    congestion_level VARCHAR(20),        -- Low | Medium | High
    congestion_score FLOAT,              -- 0-100
    confidence FLOAT,                    -- ViT confidence
    map_score FLOAT,                     -- mAP: 88.56
    fps FLOAT,
    model_used VARCHAR(50) DEFAULT 'ViT-B/16'
);

-- ──────────────────────────────────────────
-- EMISSION RECORDS
-- ──────────────────────────────────────────
CREATE TABLE emission_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    intersection_id VARCHAR(50),
    co2_kg FLOAT,                        -- Total CO2 estimate (kg/km)
    nox_mg FLOAT,
    pm25_ug FLOAT,
    aqi INTEGER,                         -- Air Quality Index
    aqi_level VARCHAR(50),               -- Good | Moderate | Unhealthy...
    vehicle_count INTEGER
);

-- ──────────────────────────────────────────
-- VIOLATIONS (ViT-detected traffic violations)
-- ──────────────────────────────────────────
CREATE TABLE violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    violation_type VARCHAR(50),          -- red_light | speeding | wrong_way | lane | overloading
    intersection_id VARCHAR(50),
    camera_id VARCHAR(50),
    severity VARCHAR(20) DEFAULT 'medium', -- low | medium | high | critical
    vehicle_plate VARCHAR(20),
    description TEXT,
    evidence_path VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending', -- pending | reviewed | actioned
    officer_id INTEGER REFERENCES users(id),
    is_severe BOOLEAN DEFAULT FALSE,
    resolved_at DATETIME
);

-- ──────────────────────────────────────────
-- ACCIDENT LOGS (ViT accident detection)
-- ──────────────────────────────────────────
CREATE TABLE accident_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    intersection_id VARCHAR(50),
    camera_id VARCHAR(50),
    severity VARCHAR(20),                -- high | critical
    accident_type VARCHAR(50),           -- multi_vehicle_collision | minor_collision
    confidence FLOAT,                    -- ViT detection confidence
    vehicles_involved INTEGER,
    description TEXT,
    evidence_path VARCHAR(255),
    status VARCHAR(20) DEFAULT 'open',   -- open | responded | closed
    emergency_dispatched BOOLEAN DEFAULT FALSE,
    officer_id INTEGER REFERENCES users(id),
    resolved_at DATETIME
);

-- ──────────────────────────────────────────
-- EMERGENCY LOGS (Emergency vehicle override)
-- ──────────────────────────────────────────
CREATE TABLE emergency_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    intersection_id VARCHAR(50),
    camera_id VARCHAR(50),
    vehicle_type VARCHAR(50),            -- Ambulance | Fire Engine | Police Car
    direction VARCHAR(20),               -- North | South | East | West
    response_time FLOAT,                 -- seconds
    override_duration INTEGER,           -- seconds signal was overridden
    resolved BOOLEAN DEFAULT FALSE
);

-- ──────────────────────────────────────────
-- SIGNAL TIMINGS (Auto/manual control)
-- ──────────────────────────────────────────
CREATE TABLE signal_timings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intersection_id VARCHAR(50) UNIQUE,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    cycle_length FLOAT,                  -- Total cycle in seconds
    north_green INTEGER DEFAULT 30,
    south_green INTEGER DEFAULT 30,
    east_green INTEGER DEFAULT 25,
    west_green INTEGER DEFAULT 25,
    is_emergency_override BOOLEAN DEFAULT FALSE,
    override_direction VARCHAR(20),
    override_expires_at DATETIME,
    mode VARCHAR(20) DEFAULT 'adaptive'  -- adaptive | manual | emergency
);

-- ──────────────────────────────────────────
-- TRAFFIC HISTORY (hourly aggregates)
-- ──────────────────────────────────────────
CREATE TABLE traffic_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    intersection_id VARCHAR(50),
    vehicle_count INTEGER DEFAULT 0,
    vehicles_per_min FLOAT DEFAULT 0.0,
    congestion_score FLOAT DEFAULT 0.0,
    avg_delay FLOAT DEFAULT 0.0,
    co2_emission FLOAT DEFAULT 0.0
);

-- ──────────────────────────────────────────
-- PREDICTIONS (TCN output)
-- ──────────────────────────────────────────
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    intersection_id VARCHAR(50),
    forecast_hour INTEGER,               -- 1-12 hours ahead
    predicted_count FLOAT,
    actual_count FLOAT,
    rmse FLOAT,                          -- TCN RMSE: 2.232
    confidence FLOAT
);

-- ──────────────────────────────────────────
-- DASHBOARD ALERTS (pushed to officer UI)
-- ──────────────────────────────────────────
CREATE TABLE dashboard_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    alert_type VARCHAR(50),              -- ACCIDENT | VIOLATION | EMERGENCY | CONGESTION
    severity VARCHAR(20),               -- low | medium | high | critical
    intersection_id VARCHAR(50),
    camera_id VARCHAR(50),
    message TEXT,
    action_required BOOLEAN DEFAULT FALSE,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by INTEGER REFERENCES users(id),
    acknowledged_at DATETIME,
    related_id INTEGER                   -- FK to accident_log or violation id
);

-- ──────────────────────────────────────────
-- KEY INDEXES
-- ──────────────────────────────────────────
CREATE INDEX idx_detections_time ON detections(timestamp);
CREATE INDEX idx_detections_cam ON detections(camera_id);
CREATE INDEX idx_violations_status ON violations(status);
CREATE INDEX idx_accidents_status ON accident_logs(status);
CREATE INDEX idx_alerts_unacked ON dashboard_alerts(acknowledged, timestamp);
CREATE INDEX idx_history_int ON traffic_history(intersection_id, timestamp);

-- ─────────────────────────────────────────────────────────
-- NEW FEATURE TABLES (v4)
-- ─────────────────────────────────────────────────────────

CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER REFERENCES users(id),
    user_name VARCHAR(100),
    user_role VARCHAR(20),
    action VARCHAR(100),
    resource VARCHAR(100),
    details TEXT,
    ip_address VARCHAR(50),
    success BOOLEAN DEFAULT TRUE
);

CREATE TABLE license_plate_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    plate_number VARCHAR(20),
    camera_id VARCHAR(50),
    intersection_id VARCHAR(50),
    confidence FLOAT,
    vehicle_type VARCHAR(30),
    linked_violation_id INTEGER REFERENCES violations(id),
    image_path VARCHAR(255),
    speed_kmh FLOAT,
    direction VARCHAR(20)
);

CREATE TABLE notification_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    channel VARCHAR(30),
    recipient VARCHAR(150),
    subject VARCHAR(200),
    message TEXT,
    alert_type VARCHAR(50),
    status VARCHAR(20) DEFAULT 'sent',
    error_msg VARCHAR(255),
    related_alert_id INTEGER,
    escalated BOOLEAN DEFAULT FALSE
);

CREATE TABLE carbon_credit_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    intersection_id VARCHAR(50),
    baseline_co2_kg FLOAT,
    actual_co2_kg FLOAT,
    co2_saved_kg FLOAT,
    carbon_credits FLOAT,
    monetary_value_usd FLOAT,
    period_hours INTEGER DEFAULT 24
);

CREATE TABLE weather_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    location VARCHAR(100),
    temperature_c FLOAT,
    humidity_pct FLOAT,
    condition VARCHAR(50),
    wind_kmh FLOAT,
    visibility_km FLOAT,
    congestion_factor FLOAT DEFAULT 1.0
);

CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    name VARCHAR(100),
    key_hash VARCHAR(255) UNIQUE,
    key_prefix VARCHAR(10),
    scope VARCHAR(200),
    scopes VARCHAR(200),
    owner_id INTEGER REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    last_used DATETIME,
    requests_today INTEGER DEFAULT 0,
    rate_limit INTEGER DEFAULT 100,
    expires_at DATETIME
);

CREATE TABLE video_clips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    camera_id VARCHAR(50),
    intersection_id VARCHAR(50),
    trigger_type VARCHAR(50),
    trigger_id INTEGER,
    duration_seconds INTEGER DEFAULT 30,
    duration_sec INTEGER DEFAULT 30,
    file_path VARCHAR(255),
    file_size_mb FLOAT,
    thumbnail_path VARCHAR(255)
);

CREATE TABLE custom_zones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    name VARCHAR(100),
    zone_type VARCHAR(30),
    polygon_coords TEXT,
    coordinates TEXT,
    color VARCHAR(20) DEFAULT '#00d4ff',
    created_by INTEGER REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    alert_on_entry BOOLEAN DEFAULT FALSE
);

CREATE TABLE officer_shifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    officer_id INTEGER REFERENCES users(id),
    shift_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    shift_start VARCHAR(10),
    shift_end VARCHAR(10),
    assigned_intersection VARCHAR(50),
    is_on_duty BOOLEAN DEFAULT FALSE,
    cases_handled INTEGER DEFAULT 0
);

-- ALTER existing tables for new fields (SQLite compatible)
-- For production PostgreSQL, use proper ALTER TABLE statements
