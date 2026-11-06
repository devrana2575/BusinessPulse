-- BusinessPulse reporting and analytical views.
-- These views are the contract shared by SQL analysis, Python reporting and
-- the Power BI MySQL connection. Keep business definitions here once.

-- ---------------------------------------------------------------------------
-- Listing detail (grain: one collected listing)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_listing_detail AS
SELECT
    l.id AS listing_id,
    l.business_id,
    l.business_name,
    c.city_id,
    c.city_name,
    c.state_name,
    c.country,
    cat.category_id,
    cat.category_name,
    cat.display_order AS category_display_order,
    s.source_id,
    s.source_name,
    s.source_type,
    s.attribution,
    l.address,
    l.phone,
    l.source_record_id,
    l.collection_date,
    l.latitude,
    l.longitude,
    l.created_at,
    l.updated_at,
    COALESCE(q.missing_phone, 0) AS missing_phone,
    COALESCE(q.missing_address, 0) AS missing_address,
    COALESCE(q.duplicate_flag, 0) AS duplicate_flag,
    COALESCE(q.potential_duplicate_flag, 0) AS potential_duplicate_flag,
    COALESCE(q.phone_valid, 0) AS phone_valid,
    COALESCE(q.address_valid, 0) AS address_valid,
    COALESCE(q.is_complete, 0) AS is_complete,
    COALESCE(q.validation_status, 'needs_review') AS validation_status,
    COALESCE(q.quality_score, 0) AS quality_score,
    CASE
        WHEN COALESCE(q.quality_score, 0) >= 80 THEN 'High (80-100)'
        WHEN COALESCE(q.quality_score, 0) >= 60 THEN 'Medium (60-79)'
        ELSE 'Low (<60)'
    END AS quality_band,
    CASE WHEN COALESCE(q.missing_phone, 1) = 0 THEN 1 ELSE 0 END AS phone_available,
    CASE WHEN COALESCE(q.missing_address, 1) = 0 THEN 1 ELSE 0 END AS address_available,
    CASE WHEN COALESCE(q.validation_status, 'needs_review') = 'valid' THEN 0 ELSE 1 END
        AS review_required,
    q.audit_timestamp
FROM listing_master l
JOIN dim_city c ON c.city_id = l.city_id
JOIN dim_category cat ON cat.category_id = l.category_id
JOIN dim_source s ON s.source_id = l.source_id
LEFT JOIN data_quality_audit q ON q.listing_id = l.id;

-- ---------------------------------------------------------------------------
-- City summary
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_city_summary AS
SELECT
    c.city_id,
    c.city_name,
    c.state_name,
    c.country,
    c.latitude,
    c.longitude,
    COUNT(l.id) AS listing_count,
    COUNT(DISTINCT l.category_id) AS categories_present,
    COUNT(DISTINCT l.source_id) AS sources_present,
    COALESCE(SUM(CASE WHEN q.missing_phone = 1 THEN 1 ELSE 0 END), 0) AS missing_phone_count,
    ROUND(100 * COALESCE(SUM(CASE WHEN q.missing_phone = 1 THEN 1 ELSE 0 END), 0)
          / NULLIF(COUNT(l.id), 0), 2) AS missing_phone_pct,
    COALESCE(SUM(CASE WHEN q.missing_address = 1 THEN 1 ELSE 0 END), 0) AS missing_address_count,
    ROUND(100 * COALESCE(SUM(CASE WHEN q.missing_address = 1 THEN 1 ELSE 0 END), 0)
          / NULLIF(COUNT(l.id), 0), 2) AS missing_address_pct,
    COALESCE(SUM(CASE WHEN q.duplicate_flag = 1 THEN 1 ELSE 0 END), 0) AS duplicate_count,
    ROUND(100 * COALESCE(SUM(CASE WHEN q.duplicate_flag = 1 THEN 1 ELSE 0 END), 0)
          / NULLIF(COUNT(l.id), 0), 2) AS duplicate_rate_pct,
    COALESCE(SUM(CASE WHEN q.is_complete = 1 THEN 1 ELSE 0 END), 0) AS complete_listings,
    ROUND(100 * COALESCE(SUM(CASE WHEN q.is_complete = 1 THEN 1 ELSE 0 END), 0)
          / NULLIF(COUNT(l.id), 0), 2) AS completeness_pct,
    ROUND(AVG(COALESCE(q.quality_score, 0)), 2) AS avg_quality_score,
    COALESCE(SUM(CASE WHEN q.validation_status = 'needs_review' THEN 1 ELSE 0 END), 0)
        AS records_requiring_review,
    ROUND(100 * COUNT(DISTINCT l.category_id)
          / NULLIF((SELECT COUNT(*) FROM dim_category), 0), 2) AS category_coverage_pct,
    ROUND(100 * COUNT(l.id)
          / NULLIF((SELECT COUNT(*) FROM listing_master), 0), 2) AS city_share_pct
FROM dim_city c
LEFT JOIN listing_master l ON l.city_id = c.city_id
LEFT JOIN data_quality_audit q ON q.listing_id = l.id
GROUP BY c.city_id, c.city_name, c.state_name, c.country, c.latitude, c.longitude
HAVING COUNT(l.id) > 0;

-- ---------------------------------------------------------------------------
-- Category summary (includes categories with zero listings)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_category_summary AS
SELECT
    cat.category_id,
    cat.category_name,
    cat.display_order,
    COUNT(l.id) AS listing_count,
    COUNT(DISTINCT l.city_id) AS cities_present,
    COUNT(DISTINCT l.source_id) AS sources_present,
    COALESCE(SUM(CASE WHEN q.missing_phone = 1 THEN 1 ELSE 0 END), 0) AS missing_phone_count,
    ROUND(100 * COALESCE(SUM(CASE WHEN q.missing_phone = 1 THEN 1 ELSE 0 END), 0)
          / NULLIF(COUNT(l.id), 0), 2) AS missing_phone_pct,
    COALESCE(SUM(CASE WHEN q.missing_address = 1 THEN 1 ELSE 0 END), 0) AS missing_address_count,
    ROUND(100 * COALESCE(SUM(CASE WHEN q.missing_address = 1 THEN 1 ELSE 0 END), 0)
          / NULLIF(COUNT(l.id), 0), 2) AS missing_address_pct,
    COALESCE(SUM(CASE WHEN q.duplicate_flag = 1 THEN 1 ELSE 0 END), 0) AS duplicate_count,
    ROUND(100 * COALESCE(SUM(CASE WHEN q.duplicate_flag = 1 THEN 1 ELSE 0 END), 0)
          / NULLIF(COUNT(l.id), 0), 2) AS duplicate_rate_pct,
    COALESCE(SUM(CASE WHEN q.is_complete = 1 THEN 1 ELSE 0 END), 0) AS complete_listings,
    ROUND(100 * COALESCE(SUM(CASE WHEN q.is_complete = 1 THEN 1 ELSE 0 END), 0)
          / NULLIF(COUNT(l.id), 0), 2) AS completeness_pct,
    ROUND(AVG(COALESCE(q.quality_score, 0)), 2) AS avg_quality_score,
    ROUND(100 * COUNT(l.id)
          / NULLIF((SELECT COUNT(*) FROM listing_master), 0), 2) AS category_share_pct,
    ROUND(100 * COUNT(DISTINCT l.city_id)
          / NULLIF((SELECT COUNT(*) FROM vw_city_summary), 0), 2) AS city_coverage_pct
FROM dim_category cat
LEFT JOIN listing_master l ON l.category_id = cat.category_id
LEFT JOIN data_quality_audit q ON q.listing_id = l.id
GROUP BY cat.category_id, cat.category_name, cat.display_order;

-- ---------------------------------------------------------------------------
-- Source summary
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_source_summary AS
SELECT
    s.source_id,
    s.source_name,
    s.source_type,
    s.license_name,
    s.attribution,
    COUNT(l.id) AS listing_count,
    COUNT(DISTINCT l.city_id) AS cities_present,
    COUNT(DISTINCT l.category_id) AS categories_present,
    COALESCE(SUM(CASE WHEN q.missing_phone = 1 THEN 1 ELSE 0 END), 0) AS missing_phone_count,
    ROUND(100 * COALESCE(SUM(CASE WHEN q.missing_phone = 1 THEN 1 ELSE 0 END), 0)
          / NULLIF(COUNT(l.id), 0), 2) AS missing_phone_pct,
    COALESCE(SUM(CASE WHEN q.missing_address = 1 THEN 1 ELSE 0 END), 0) AS missing_address_count,
    ROUND(100 * COALESCE(SUM(CASE WHEN q.missing_address = 1 THEN 1 ELSE 0 END), 0)
          / NULLIF(COUNT(l.id), 0), 2) AS missing_address_pct,
    COALESCE(SUM(CASE WHEN q.duplicate_flag = 1 THEN 1 ELSE 0 END), 0) AS duplicate_count,
    ROUND(100 * COALESCE(SUM(CASE WHEN q.duplicate_flag = 1 THEN 1 ELSE 0 END), 0)
          / NULLIF(COUNT(l.id), 0), 2) AS duplicate_rate_pct,
    COALESCE(SUM(CASE WHEN q.is_complete = 1 THEN 1 ELSE 0 END), 0) AS complete_listings,
    ROUND(100 * COALESCE(SUM(CASE WHEN q.is_complete = 1 THEN 1 ELSE 0 END), 0)
          / NULLIF(COUNT(l.id), 0), 2) AS completeness_pct,
    ROUND(AVG(COALESCE(q.quality_score, 0)), 2) AS avg_quality_score,
    ROUND(100 * COUNT(l.id)
          / NULLIF((SELECT COUNT(*) FROM listing_master), 0), 2) AS source_share_pct
FROM dim_source s
LEFT JOIN listing_master l ON l.source_id = s.source_id
LEFT JOIN data_quality_audit q ON q.listing_id = l.id
GROUP BY s.source_id, s.source_name, s.source_type, s.license_name, s.attribution;

-- ---------------------------------------------------------------------------
-- Overall data-quality summary (one row)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_data_quality_summary AS
SELECT
    COUNT(l.id) AS total_listings,
    COALESCE(SUM(CASE WHEN q.missing_phone = 1 THEN 1 ELSE 0 END), 0) AS missing_phone_count,
    ROUND(100 * COALESCE(SUM(CASE WHEN q.missing_phone = 1 THEN 1 ELSE 0 END), 0)
          / NULLIF(COUNT(l.id), 0), 2) AS missing_phone_pct,
    COALESCE(SUM(CASE WHEN q.missing_address = 1 THEN 1 ELSE 0 END), 0) AS missing_address_count,
    ROUND(100 * COALESCE(SUM(CASE WHEN q.missing_address = 1 THEN 1 ELSE 0 END), 0)
          / NULLIF(COUNT(l.id), 0), 2) AS missing_address_pct,
    COALESCE(SUM(CASE WHEN q.duplicate_flag = 1 THEN 1 ELSE 0 END), 0) AS duplicate_count,
    ROUND(100 * COALESCE(SUM(CASE WHEN q.duplicate_flag = 1 THEN 1 ELSE 0 END), 0)
          / NULLIF(COUNT(l.id), 0), 2) AS duplicate_rate_pct,
    COALESCE(SUM(CASE WHEN q.potential_duplicate_flag = 1 THEN 1 ELSE 0 END), 0)
        AS potential_duplicate_count,
    COALESCE(SUM(CASE WHEN q.is_complete = 1 THEN 1 ELSE 0 END), 0) AS complete_listings,
    ROUND(100 * COALESCE(SUM(CASE WHEN q.is_complete = 1 THEN 1 ELSE 0 END), 0)
          / NULLIF(COUNT(l.id), 0), 2) AS completeness_pct,
    COALESCE(SUM(CASE WHEN q.validation_status = 'valid' THEN 1 ELSE 0 END), 0)
        AS valid_listings,
    COALESCE(SUM(CASE WHEN q.validation_status = 'needs_review' THEN 1 ELSE 0 END), 0)
        AS records_requiring_review,
    ROUND(AVG(COALESCE(q.quality_score, 0)), 2) AS avg_quality_score,
    MIN(q.quality_score) AS min_quality_score,
    MAX(q.quality_score) AS max_quality_score
FROM listing_master l
LEFT JOIN data_quality_audit q ON q.listing_id = l.id;

-- ---------------------------------------------------------------------------
-- City x category coverage universe (cities with >=1 listing x all categories)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_city_category_coverage AS
SELECT
    c.city_id,
    c.city_name,
    c.state_name,
    cat.category_id,
    cat.category_name,
    cat.display_order,
    COALESCE(x.listing_count, 0) AS listing_count,
    cs.listing_count AS city_total,
    COALESCE(cat_s.listing_count, 0) AS category_total,
    t.total_listings,
    ROUND(100 * COALESCE(x.listing_count, 0) / NULLIF(cs.listing_count, 0), 2)
        AS category_share_in_city_pct,
    ROUND(100 * COALESCE(cat_s.listing_count, 0) / NULLIF(t.total_listings, 0), 2)
        AS national_category_share_pct,
    ROUND(
        (COALESCE(x.listing_count, 0) / NULLIF(cs.listing_count, 0))
        / NULLIF(COALESCE(cat_s.listing_count, 0) / NULLIF(t.total_listings, 0), 0),
        4
    ) AS relative_representation,
    CASE WHEN COALESCE(x.listing_count, 0) > 0 THEN 1 ELSE 0 END AS is_covered,
    cs.categories_present,
    (SELECT COUNT(*) FROM dim_category) AS total_categories,
    cs.category_coverage_pct,
    cs.completeness_pct AS city_completeness_pct,
    cs.avg_quality_score AS city_avg_quality_score,
    cfg.min_city_listings,
    cfg.min_category_national_count,
    CASE
        WHEN cs.listing_count >= cfg.min_city_listings
         AND COALESCE(cat_s.listing_count, 0) >= cfg.min_category_national_count
        THEN 1 ELSE 0
    END AS is_candidate,
    CASE
        WHEN COALESCE(x.listing_count, 0) = 0 THEN 'No listings in this city-category'
        WHEN ROUND(
            (COALESCE(x.listing_count, 0) / NULLIF(cs.listing_count, 0))
            / NULLIF(COALESCE(cat_s.listing_count, 0) / NULLIF(t.total_listings, 0), 0),
            4
        ) < 0.50 THEN 'Below national baseline'
        WHEN ROUND(
            (COALESCE(x.listing_count, 0) / NULLIF(cs.listing_count, 0))
            / NULLIF(COALESCE(cat_s.listing_count, 0) / NULLIF(t.total_listings, 0), 0),
            4
        ) < 1.00 THEN 'Slightly below baseline'
        ELSE 'At or above baseline'
    END AS coverage_status
FROM dim_city c
JOIN vw_city_summary cs ON cs.city_id = c.city_id
CROSS JOIN dim_category cat
LEFT JOIN vw_category_summary cat_s ON cat_s.category_id = cat.category_id
LEFT JOIN (
    SELECT city_id, category_id, COUNT(*) AS listing_count
    FROM listing_master
    GROUP BY city_id, category_id
) x ON x.city_id = c.city_id AND x.category_id = cat.category_id
CROSS JOIN (SELECT COUNT(*) AS total_listings FROM listing_master) t
CROSS JOIN opportunity_config cfg
WHERE cfg.config_id = 1;

-- ---------------------------------------------------------------------------
-- Transparent market-opportunity score
--
-- Underrepresentation = max(0, 1 - relative representation)
--   relative representation = category share in city / national category share
-- City breadth gap = 1 - (categories present in city / total categories)
-- Reliability = city completeness % (phone + address + not duplicate)
--
-- opportunity_score = 100 * (
--   0.60 * underrepresentation
-- + 0.25 * city breadth gap
-- + 0.15 * reliability
-- )
--
-- A low listing count is evidence of underrepresentation in THIS COLLECTED
-- SAMPLE. It is not proof of low competition, unmet demand, or market size.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_market_opportunity AS
SELECT
    v.city_id,
    v.city_name,
    v.state_name,
    v.category_id,
    v.category_name,
    v.listing_count,
    v.city_total,
    v.category_total,
    v.total_listings,
    v.category_share_in_city_pct,
    v.national_category_share_pct,
    v.relative_representation,
    v.is_covered,
    v.categories_present,
    v.total_categories,
    v.category_coverage_pct AS city_category_coverage_pct,
    v.city_completeness_pct,
    v.city_avg_quality_score,
    v.is_candidate,
    v.coverage_status,
    ROUND(GREATEST(0, 1 - COALESCE(v.relative_representation, 0)), 4)
        AS underrepresentation_index,
    ROUND(1 - COALESCE(v.category_coverage_pct, 0) / 100, 4) AS city_breadth_gap,
    ROUND(COALESCE(v.city_completeness_pct, 0) / 100, 4) AS reliability_index,
    ROUND(100 * cfg.underrepresentation_weight
          * GREATEST(0, 1 - COALESCE(v.relative_representation, 0)), 2)
        AS underrepresentation_points,
    ROUND(100 * cfg.city_breadth_weight
          * (1 - COALESCE(v.category_coverage_pct, 0) / 100), 2)
        AS breadth_points,
    ROUND(100 * cfg.reliability_weight
          * COALESCE(v.city_completeness_pct, 0) / 100, 2)
        AS reliability_points,
    ROUND(
        100 * (
            cfg.underrepresentation_weight
                * GREATEST(0, 1 - COALESCE(v.relative_representation, 0))
            + cfg.city_breadth_weight
                * (1 - COALESCE(v.category_coverage_pct, 0) / 100)
            + cfg.reliability_weight
                * COALESCE(v.city_completeness_pct, 0) / 100
        ),
        2
    ) AS opportunity_score,
    CASE
        WHEN v.is_candidate = 0 THEN 'Insufficient evidence'
        WHEN ROUND(
            100 * (
                cfg.underrepresentation_weight
                    * GREATEST(0, 1 - COALESCE(v.relative_representation, 0))
                + cfg.city_breadth_weight
                    * (1 - COALESCE(v.category_coverage_pct, 0) / 100)
                + cfg.reliability_weight
                    * COALESCE(v.city_completeness_pct, 0) / 100
            ), 2
        ) >= cfg.high_threshold THEN 'High'
        WHEN ROUND(
            100 * (
                cfg.underrepresentation_weight
                    * GREATEST(0, 1 - COALESCE(v.relative_representation, 0))
                + cfg.city_breadth_weight
                    * (1 - COALESCE(v.category_coverage_pct, 0) / 100)
                + cfg.reliability_weight
                    * COALESCE(v.city_completeness_pct, 0) / 100
            ), 2
        ) >= cfg.medium_threshold THEN 'Medium'
        ELSE 'Low'
    END AS opportunity_tier,
    cfg.underrepresentation_weight,
    cfg.city_breadth_weight,
    cfg.reliability_weight,
    cfg.high_threshold,
    cfg.medium_threshold,
    CONCAT(
        'Score v1.0 = 100 x (',
        cfg.underrepresentation_weight, ' x underrepresentation + ',
        cfg.city_breadth_weight, ' x city breadth gap + ',
        cfg.reliability_weight, ' x completeness). ',
        'Low counts indicate underrepresentation in collected listings only.'
    ) AS methodology_note
FROM vw_city_category_coverage v
JOIN opportunity_config cfg ON cfg.config_id = 1;
