-- Migration: Add Notification Subscriptions Table
-- Date: 2026-01-24
-- Purpose: Store Push Notification subscriptions securely in DB instead of JSON file.

CREATE TABLE IF NOT EXISTS notification_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL UNIQUE,
    p256dh VARCHAR(255) NOT NULL,
    auth VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_subscriptions_user_id ON notification_subscriptions(user_id);
