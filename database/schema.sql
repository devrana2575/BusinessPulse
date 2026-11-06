-- BusinessPulse MySQL schema
-- MySQL 9.x / InnoDB / utf8mb4
--
-- This file creates tables only. Lookup values live in seed_data.sql,
-- secondary indexes in indexes.sql, and BI/analytics views in views.sql.
-- Apply through scripts/setup_database.py so the target database is explicit.

SET NAMES utf8mb4;
SET time_zone = '+00:00';

CREATE TABLE IF NOT EXISTS dim_city (
    city_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    city_name VARCHAR(100) NOT NULL,
    state_name VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL DEFAULT 'India',
    latitude DECIMAL(10, 7) NULL,
    longitude DECIMAL(10, 7) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (city_id),
    UNIQUE KEY uq_dim_city_name (city_name)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS dim_category (
    category_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    category_name VARCHAR(100) NOT NULL,
    display_order SMALLINT UNSIGNED NOT NULL DEFAULT 999,
    description VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (category_id),
    UNIQUE KEY uq_dim_category_name (category_name)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS dim_source (
    source_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    source_name VARCHAR(150) NOT NULL,
    source_type VARCHAR(100) NOT NULL,
    source_url VARCHAR(500) NULL,
    license_name VARCHAR(150) NOT NULL,
    license_url VARCHAR(500) NULL,
    attribution VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_id),
    UNIQUE KEY uq_dim_source_name (source_name)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS import_batches (
    batch_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    source_id INT UNSIGNED NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_hash CHAR(64) NOT NULL,
    rows_received INT UNSIGNED NOT NULL DEFAULT 0,
    rows_inserted INT UNSIGNED NOT NULL DEFAULT 0,
    rows_rejected INT UNSIGNED NOT NULL DEFAULT 0,
    rows_flagged_duplicate INT UNSIGNED NOT NULL DEFAULT 0,
    imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM('started', 'completed', 'failed') NOT NULL DEFAULT 'started',
    notes VARCHAR(500) NULL,
    PRIMARY KEY (batch_id),
    UNIQUE KEY uq_import_source_hash (source_id, file_hash),
    KEY idx_import_status (status),
    CONSTRAINT fk_import_source FOREIGN KEY (source_id)
        REFERENCES dim_source (source_id) ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS listing_master (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    business_id VARCHAR(40) NOT NULL,
    business_name VARCHAR(255) NOT NULL,
    category_id INT UNSIGNED NOT NULL,
    city_id INT UNSIGNED NOT NULL,
    address VARCHAR(500) NULL,
    phone VARCHAR(64) NULL,
    source_id INT UNSIGNED NOT NULL,
    source_record_id VARCHAR(64) NOT NULL,
    collection_date DATE NOT NULL,
    latitude DECIMAL(10, 7) NULL,
    longitude DECIMAL(10, 7) NULL,
    created_at DATETIME NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_listing_business_id (business_id),
    UNIQUE KEY uq_listing_source_record (source_id, source_record_id),
    CONSTRAINT fk_listing_city FOREIGN KEY (city_id)
        REFERENCES dim_city (city_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_listing_category FOREIGN KEY (category_id)
        REFERENCES dim_category (category_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_listing_source FOREIGN KEY (source_id)
        REFERENCES dim_source (source_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_listing_collection_date CHECK (collection_date >= '2000-01-01')
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS data_quality_audit (
    audit_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    listing_id BIGINT UNSIGNED NOT NULL,
    missing_phone BOOLEAN NOT NULL DEFAULT FALSE,
    missing_address BOOLEAN NOT NULL DEFAULT FALSE,
    duplicate_flag BOOLEAN NOT NULL DEFAULT FALSE,
    potential_duplicate_flag BOOLEAN NOT NULL DEFAULT FALSE,
    phone_valid BOOLEAN NOT NULL DEFAULT FALSE,
    address_valid BOOLEAN NOT NULL DEFAULT FALSE,
    is_complete BOOLEAN NOT NULL DEFAULT FALSE,
    validation_status ENUM('valid', 'needs_review', 'invalid') NOT NULL,
    quality_score DECIMAL(5, 2) NOT NULL,
    audit_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (audit_id),
    UNIQUE KEY uq_audit_listing (listing_id),
    CONSTRAINT fk_audit_listing FOREIGN KEY (listing_id)
        REFERENCES listing_master (id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT chk_audit_quality_score CHECK (quality_score BETWEEN 0 AND 100)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS listing_rejects (
    reject_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    import_batch_id BIGINT UNSIGNED NULL,
    source_record_id VARCHAR(64) NULL,
    business_name VARCHAR(255) NULL,
    city_name VARCHAR(100) NULL,
    category_name VARCHAR(100) NULL,
    rejection_reason VARCHAR(500) NOT NULL,
    raw_record JSON NOT NULL,
    rejected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (reject_id),
    KEY idx_reject_batch (import_batch_id),
    CONSTRAINT fk_reject_batch FOREIGN KEY (import_batch_id)
        REFERENCES import_batches (batch_id) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS opportunity_config (
    config_id TINYINT UNSIGNED NOT NULL,
    underrepresentation_weight DECIMAL(5, 4) NOT NULL,
    city_breadth_weight DECIMAL(5, 4) NOT NULL,
    reliability_weight DECIMAL(5, 4) NOT NULL,
    high_threshold DECIMAL(5, 2) NOT NULL DEFAULT 60.00,
    medium_threshold DECIMAL(5, 2) NOT NULL DEFAULT 40.00,
    min_city_listings SMALLINT UNSIGNED NOT NULL DEFAULT 20,
    min_category_national_count SMALLINT UNSIGNED NOT NULL DEFAULT 5,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (config_id),
    CONSTRAINT chk_opportunity_weights_sum CHECK (
        ROUND(underrepresentation_weight + city_breadth_weight + reliability_weight, 4) = 1.0000
    )
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
