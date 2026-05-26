-- Ganji Protocol PostgreSQL Schema
-- Migration 001: Initial tables for rates, signals, and P2P data

CREATE TABLE IF NOT EXISTS rates (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    currency VARCHAR(10) NOT NULL,
    close DECIMAL(12, 6) NOT NULL,
    source VARCHAR(50) NOT NULL,
    flag VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, currency, source),
    INDEX idx_currency_date (currency, date DESC)
);

CREATE TABLE IF NOT EXISTS p2p_snapshots (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    min_price DECIMAL(12, 4) NOT NULL,
    max_price DECIMAL(12, 4) NOT NULL,
    mean_price DECIMAL(12, 4) NOT NULL,
    spread DECIMAL(12, 4) NOT NULL,
    ad_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(timestamp)
);

CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    signal_id VARCHAR(50) NOT NULL UNIQUE,
    pair VARCHAR(20) NOT NULL DEFAULT 'KES/USD',
    signal_date DATE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    pipeline_version VARCHAR(20) NOT NULL,
    
    -- Detection fields
    cips_score INTEGER NOT NULL,
    confidence VARCHAR(20) NOT NULL,
    confidence_raw VARCHAR(20),
    direction VARCHAR(30) NOT NULL,
    sequence_pattern BOOLEAN NOT NULL,
    cpii_contributed BOOLEAN NOT NULL,
    
    -- Component scores
    z_score_value DECIMAL(8, 4),
    z_score_points INTEGER,
    cpii_fired BOOLEAN,
    cpii_points INTEGER,
    gvci_value DECIMAL(8, 4),
    gvci_points INTEGER,
    nlp_tone VARCHAR(50),
    nlp_points INTEGER,
    bpps_premium DECIMAL(8, 6),
    bpps_points INTEGER,
    
    -- Context
    calendar_flags TEXT,
    signal_context TEXT,
    regulatory_note TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX idx_signal_date ON signals(signal_date DESC);
CREATE INDEX idx_signal_confidence ON signals(confidence);
CREATE INDEX idx_signal_id ON signals(signal_id);

-- Audit log for pipeline runs
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id BIGSERIAL PRIMARY KEY,
    run_date DATE NOT NULL,
    mode VARCHAR(20) NOT NULL, -- 'daily' or 'historical'
    status VARCHAR(20) NOT NULL, -- 'OK', 'DEGRADED', 'ERROR'
    rates_saved INTEGER,
    p2p_saved BOOLEAN,
    sources_used TEXT,
    errors TEXT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_ms BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pipeline_date ON pipeline_runs(run_date DESC);
