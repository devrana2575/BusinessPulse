-- BusinessPulse secondary indexes
-- Foreign-key columns are already indexed automatically by InnoDB.
-- Apply after schema.sql. setup_database.py tolerates duplicate-index errors
-- when re-applying to an existing database.

CREATE INDEX idx_listing_city_category
    ON listing_master (city_id, category_id);

CREATE INDEX idx_listing_collection_date
    ON listing_master (collection_date);

CREATE INDEX idx_listing_business_name
    ON listing_master (business_name);

CREATE INDEX idx_listing_category_source
    ON listing_master (category_id, source_id);

CREATE INDEX idx_audit_validation_status
    ON data_quality_audit (validation_status);

CREATE INDEX idx_audit_duplicate
    ON data_quality_audit (duplicate_flag);

CREATE INDEX idx_audit_quality_score
    ON data_quality_audit (quality_score);

CREATE INDEX idx_audit_complete
    ON data_quality_audit (is_complete);

CREATE INDEX idx_reject_rejected_at
    ON listing_rejects (rejected_at);

CREATE INDEX idx_import_imported_at
    ON import_batches (imported_at);
