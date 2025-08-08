-- Surfboard Lamp Backend Database Schema
-- PostgreSQL database schema for lamp registry and activity logging

-- Lamp Registry Table
CREATE TABLE lamp_registry (
    lamp_id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    location_index INTEGER NOT NULL,
    brightness INTEGER DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    last_seen TIMESTAMP
);

-- Activity Log Table
CREATE TABLE activity_log (
    id BIGSERIAL PRIMARY KEY,
    lamp_id UUID,
    activity_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lamp_id) REFERENCES lamp_registry(lamp_id) ON DELETE SET NULL
);

-- Performance Indexes
CREATE INDEX idx_lamp_registry_email ON lamp_registry(email);
CREATE INDEX idx_lamp_registry_location ON lamp_registry(location_index);
CREATE INDEX idx_activity_log_lamp_time ON activity_log(lamp_id, created_at);