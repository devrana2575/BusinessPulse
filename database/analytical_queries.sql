-- ============================================================================
-- BusinessPulse analytical SQL
-- Every query answers a business question. Run with:
--   python -m analytics.sql_analysis.run_queries
-- The runner splits on the "-- QUERY:" markers and exports each result to CSV.
-- ============================================================================

-- QUERY: Q01 | Dataset health snapshot
-- Business question: How many listings are in the collected sample, and how
-- complete are the core contact fields overall?
SELECT
    total_listings,
    missing_phone_count,
    missing_phone_pct,
    missing_address_count,
    missing_address_pct,
    duplicate_count,
    duplicate_rate_pct,
    complete_listings,
    completeness_pct,
    avg_quality_score,
    records_requiring_review
FROM vw_data_quality_summary;

-- QUERY: Q02 | Listings by city
-- Business question: How are the collected listings distributed across cities?
SELECT
    city_name,
    state_name,
    listing_count,
    categories_present,
    city_share_pct,
    completeness_pct,
    avg_quality_score
FROM vw_city_summary
ORDER BY listing_count DESC, city_name;

-- QUERY: Q03 | Top 10 cities by listing count
-- Business question: Which cities have the strongest representation in the
-- collected sample?
SELECT
    city_name,
    listing_count,
    categories_present,
    city_share_pct,
    RANK() OVER (ORDER BY listing_count DESC) AS city_rank
FROM vw_city_summary
ORDER BY listing_count DESC, city_name
LIMIT 10;

-- QUERY: Q04 | Bottom 10 cities by listing count
-- Business question: Which cities have the weakest representation in the
-- collected sample? (Not a demand measure.)
SELECT
    city_name,
    listing_count,
    categories_present,
    city_share_pct,
    RANK() OVER (ORDER BY listing_count ASC) AS low_representation_rank
FROM vw_city_summary
ORDER BY listing_count ASC, city_name
LIMIT 10;

-- QUERY: Q05 | City concentration and cumulative share
-- Business question: How concentrated are listings in the largest cities?
WITH city_counts AS (
    SELECT city_name, listing_count
    FROM vw_city_summary
),
totals AS (
    SELECT SUM(listing_count) AS total_listings FROM city_counts
)
SELECT
    cc.city_name,
    cc.listing_count,
    ROUND(100 * cc.listing_count / NULLIF(t.total_listings, 0), 2) AS city_share_pct,
    ROUND(
        100 * SUM(cc.listing_count) OVER (
            ORDER BY cc.listing_count DESC, cc.city_name
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) / NULLIF(t.total_listings, 0),
        2
    ) AS cumulative_share_pct
FROM city_counts cc
CROSS JOIN totals t
ORDER BY cc.listing_count DESC, cc.city_name;

-- QUERY: Q06 | City ranking with multiple window functions
-- Business question: How do cities rank, and are there ties that a single
-- leaderboard position would hide?
SELECT
    city_name,
    listing_count,
    RANK() OVER (ORDER BY listing_count DESC) AS rank_with_ties,
    DENSE_RANK() OVER (ORDER BY listing_count DESC) AS dense_rank_with_ties,
    ROW_NUMBER() OVER (ORDER BY listing_count DESC, city_name) AS row_number_stable
FROM vw_city_summary
ORDER BY listing_count DESC, city_name;

-- QUERY: Q07 | City-wise category distribution and category rank
-- Business question: Within each city, which categories dominate, and what
-- share of that city do they represent?
SELECT
    c.city_name,
    cat.category_name,
    COUNT(*) AS listing_count,
    ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY c.city_id), 2)
        AS pct_within_city,
    RANK() OVER (PARTITION BY c.city_id ORDER BY COUNT(*) DESC) AS category_rank_in_city
FROM listing_master l
JOIN dim_city c ON c.city_id = l.city_id
JOIN dim_category cat ON cat.category_id = l.category_id
GROUP BY c.city_id, c.city_name, cat.category_id, cat.category_name
ORDER BY c.city_name, category_rank_in_city, cat.category_name;

-- QUERY: Q08 | Category summary and share
-- Business question: How large is each category, and across how many cities
-- does it appear?
SELECT
    category_name,
    listing_count,
    category_share_pct,
    cities_present,
    city_coverage_pct,
    completeness_pct,
    RANK() OVER (ORDER BY listing_count DESC) AS category_rank
FROM vw_category_summary
ORDER BY listing_count DESC, category_name;

-- QUERY: Q09 | Most common categories
-- Business question: Which categories are most common in the collected data?
SELECT
    category_name,
    listing_count,
    category_share_pct,
    cities_present
FROM vw_category_summary
ORDER BY listing_count DESC, category_name
LIMIT 5;

-- QUERY: Q10 | Least represented categories
-- Business question: Which categories are least represented in the collected
-- data, including categories with zero listings?
SELECT
    category_name,
    listing_count,
    category_share_pct,
    cities_present,
    city_coverage_pct
FROM vw_category_summary
ORDER BY listing_count ASC, category_name
LIMIT 5;

-- QUERY: Q11 | Category coverage across the city universe
-- Business question: In how many of the collected cities does each category
-- appear at least once?
SELECT
    category_name,
    cities_present,
    (SELECT COUNT(*) FROM vw_city_summary) AS cities_with_listings,
    city_coverage_pct,
    listing_count
FROM vw_category_summary
ORDER BY city_coverage_pct DESC, listing_count DESC;

-- QUERY: Q12 | City category diversity
-- Business question: Which cities have the broadest category mix in the
-- collected sample?
SELECT
    city_name,
    listing_count,
    categories_present,
    (SELECT COUNT(*) FROM dim_category) AS total_categories,
    category_coverage_pct,
    RANK() OVER (ORDER BY categories_present DESC, listing_count DESC) AS diversity_rank
FROM vw_city_summary
ORDER BY categories_present DESC, listing_count DESC;

-- QUERY: Q13 | Missing phone by city
-- Business question: Where is phone coverage weakest across the collected
-- cities?
SELECT
    city_name,
    listing_count,
    missing_phone_count,
    missing_phone_pct,
    phone_valid_listings,
    ROUND(100 * phone_valid_listings / NULLIF(listing_count, 0), 2) AS valid_phone_pct
FROM (
    SELECT
        c.city_id,
        c.city_name,
        COUNT(*) AS listing_count,
        SUM(CASE WHEN q.missing_phone = 1 THEN 1 ELSE 0 END) AS missing_phone_count,
        ROUND(100 * SUM(CASE WHEN q.missing_phone = 1 THEN 1 ELSE 0 END)
              / NULLIF(COUNT(*), 0), 2) AS missing_phone_pct,
        SUM(CASE WHEN q.phone_valid = 1 THEN 1 ELSE 0 END) AS phone_valid_listings
    FROM listing_master l
    JOIN dim_city c ON c.city_id = l.city_id
    JOIN data_quality_audit q ON q.listing_id = l.id
    GROUP BY c.city_id, c.city_name
) city_quality
ORDER BY missing_phone_pct DESC, city_name;

-- QUERY: Q14 | Missing address by city
-- Business question: Where is address coverage weakest across the collected
-- cities?
SELECT
    city_name,
    listing_count,
    missing_address_count,
    missing_address_pct,
    address_valid_listings,
    ROUND(100 * address_valid_listings / NULLIF(listing_count, 0), 2) AS valid_address_pct
FROM (
    SELECT
        c.city_id,
        c.city_name,
        COUNT(*) AS listing_count,
        SUM(CASE WHEN q.missing_address = 1 THEN 1 ELSE 0 END) AS missing_address_count,
        ROUND(100 * SUM(CASE WHEN q.missing_address = 1 THEN 1 ELSE 0 END)
              / NULLIF(COUNT(*), 0), 2) AS missing_address_pct,
        SUM(CASE WHEN q.address_valid = 1 THEN 1 ELSE 0 END) AS address_valid_listings
    FROM listing_master l
    JOIN dim_city c ON c.city_id = l.city_id
    JOIN data_quality_audit q ON q.listing_id = l.id
    GROUP BY c.city_id, c.city_name
) city_quality
ORDER BY missing_address_pct DESC, city_name;

-- QUERY: Q15 | Duplicate records requiring review
-- Business question: Which records were flagged as exact duplicates, and what
-- evidence supports the flag?
SELECT
    business_id,
    business_name,
    city_name,
    category_name,
    address,
    phone,
    source_record_id,
    quality_score,
    validation_status
FROM vw_listing_detail
WHERE duplicate_flag = 1
ORDER BY city_name, business_name, business_id;

-- QUERY: Q16 | Duplicate count by city
-- Business question: Which cities have the highest duplicate rate after
-- normalisation?
SELECT
    city_name,
    listing_count,
    duplicate_count,
    duplicate_rate_pct,
    RANK() OVER (ORDER BY duplicate_rate_pct DESC) AS duplicate_rate_rank
FROM vw_city_summary
ORDER BY duplicate_rate_pct DESC, city_name;

-- QUERY: Q17 | Completeness by city
-- Business question: Which cities have the most complete records under the
-- documented completeness rule?
SELECT
    city_name,
    listing_count,
    complete_listings,
    completeness_pct,
    avg_quality_score,
    records_requiring_review,
    RANK() OVER (ORDER BY completeness_pct DESC) AS completeness_rank
FROM vw_city_summary
ORDER BY completeness_pct DESC, city_name;

-- QUERY: Q18 | Completeness by category
-- Business question: Which categories have the strongest contact-data
-- completeness?
SELECT
    category_name,
    listing_count,
    complete_listings,
    completeness_pct,
    missing_phone_pct,
    missing_address_pct,
    RANK() OVER (ORDER BY completeness_pct DESC) AS completeness_rank
FROM vw_category_summary
ORDER BY completeness_pct DESC, category_name;

-- QUERY: Q19 | Completeness by source
-- Business question: How complete is each source, and how much of the
-- dataset does it represent?
SELECT
    source_name,
    listing_count,
    source_share_pct,
    complete_listings,
    completeness_pct,
    missing_phone_pct,
    missing_address_pct,
    duplicate_rate_pct,
    avg_quality_score
FROM vw_source_summary
ORDER BY listing_count DESC;

-- QUERY: Q20 | Records requiring review
-- Business question: Which records should an analyst inspect first because
-- they are incomplete, invalid or duplicated?
SELECT
    business_id,
    business_name,
    city_name,
    category_name,
    source_name,
    phone_available,
    address_available,
    duplicate_flag,
    quality_score,
    validation_status,
    quality_band
FROM vw_listing_detail
WHERE validation_status = 'needs_review'
  AND (quality_score < 60 OR (missing_phone = 1 AND missing_address = 1))
ORDER BY quality_score ASC, city_name, business_name
LIMIT 100;

-- QUERY: Q21 | Missing-field rate by source
-- Business question: Are contact-field gaps concentrated in one source?
SELECT
    source_name,
    listing_count,
    missing_phone_count,
    missing_phone_pct,
    missing_address_count,
    missing_address_pct
FROM vw_source_summary
ORDER BY missing_phone_pct DESC, missing_address_pct DESC;

-- QUERY: Q22 | Duplicate rate by source
-- Business question: Does duplicate risk differ by source?
SELECT
    source_name,
    listing_count,
    duplicate_count,
    duplicate_rate_pct,
    potential_duplicate_count
FROM (
    SELECT
        s.source_name,
        COUNT(l.id) AS listing_count,
        SUM(CASE WHEN q.duplicate_flag = 1 THEN 1 ELSE 0 END) AS duplicate_count,
        ROUND(100 * SUM(CASE WHEN q.duplicate_flag = 1 THEN 1 ELSE 0 END)
              / NULLIF(COUNT(l.id), 0), 2) AS duplicate_rate_pct,
        SUM(CASE WHEN q.potential_duplicate_flag = 1 THEN 1 ELSE 0 END)
            AS potential_duplicate_count
    FROM dim_source s
    LEFT JOIN listing_master l ON l.source_id = s.source_id
    LEFT JOIN data_quality_audit q ON q.listing_id = l.id
    GROUP BY s.source_id, s.source_name
) source_quality
ORDER BY duplicate_rate_pct DESC, source_name;

-- QUERY: Q23 | Source listing counts and concentration
-- Business question: Is the dataset dependent on a single source?
SELECT
    source_name,
    source_type,
    listing_count,
    source_share_pct,
    cities_present,
    categories_present,
    license_name
FROM vw_source_summary
ORDER BY listing_count DESC;

-- QUERY: Q24 | City-category coverage matrix
-- Business question: Which city-category combinations are present, and how
-- far is each combination from the national category baseline?
SELECT
    city_name,
    category_name,
    listing_count,
    city_total,
    category_share_in_city_pct,
    national_category_share_pct,
    relative_representation,
    is_covered,
    coverage_status
FROM vw_city_category_coverage
ORDER BY city_name, display_order;

-- QUERY: Q25 | Underrepresented categories within cities
-- Business question: Which city-category combinations are materially below
-- the national category baseline and deserve further research?
SELECT
    city_name,
    category_name,
    listing_count,
    city_total,
    category_share_in_city_pct,
    national_category_share_pct,
    relative_representation,
    opportunity_score,
    opportunity_tier,
    coverage_status
FROM vw_market_opportunity
WHERE is_candidate = 1
  AND relative_representation < 0.50
ORDER BY opportunity_score DESC, relative_representation ASC
LIMIT 60;

-- QUERY: Q26 | Cities with low category coverage
-- Business question: Which cities have the narrowest category mix in the
-- collected sample?
SELECT
    city_name,
    listing_count,
    categories_present,
    (SELECT COUNT(*) FROM dim_category) AS total_categories,
    category_coverage_pct,
    RANK() OVER (ORDER BY category_coverage_pct ASC) AS low_coverage_rank
FROM vw_city_summary
WHERE category_coverage_pct < 75
ORDER BY category_coverage_pct ASC, listing_count DESC;

-- QUERY: Q27 | Category concentration by city
-- Business question: Is each city dominated by one category, or is its mix
-- relatively balanced? HHI is computed on within-city category shares.
WITH city_category AS (
    SELECT
        c.city_name,
        cat.category_name,
        COUNT(*) AS listing_count,
        SUM(COUNT(*)) OVER (PARTITION BY c.city_id) AS city_total
    FROM listing_master l
    JOIN dim_city c ON c.city_id = l.city_id
    JOIN dim_category cat ON cat.category_id = l.category_id
    GROUP BY c.city_id, c.city_name, cat.category_id, cat.category_name
),
shares AS (
    SELECT
        city_name,
        category_name,
        listing_count,
        city_total,
        1.0 * listing_count / NULLIF(city_total, 0) AS category_share
    FROM city_category
),
hhi AS (
    SELECT
        city_name,
        ROUND(SUM(category_share * category_share) * 10000, 2) AS category_hhi
    FROM shares
    GROUP BY city_name
),
ranked AS (
    SELECT
        shares.city_name,
        shares.category_name,
        shares.listing_count,
        shares.city_total,
        ROUND(100 * shares.category_share, 2) AS top_category_share_pct,
        ROW_NUMBER() OVER (PARTITION BY shares.city_name ORDER BY shares.listing_count DESC) AS rn
    FROM shares
)
SELECT
    ranked.city_name,
    ranked.category_name AS top_category,
    ranked.listing_count AS top_category_count,
    ranked.city_total,
    ranked.top_category_share_pct,
    hhi.category_hhi
FROM ranked
JOIN hhi ON hhi.city_name = ranked.city_name
WHERE ranked.rn = 1
ORDER BY ranked.top_category_share_pct DESC, ranked.city_name;

-- QUERY: Q28 | Transparent opportunity ranking
-- Business question: Which city-category combinations have the highest
-- opportunity score under the documented methodology?
SELECT
    city_name,
    category_name,
    listing_count,
    city_total,
    relative_representation,
    underrepresentation_index,
    city_breadth_gap,
    reliability_index,
    underrepresentation_points,
    breadth_points,
    reliability_points,
    opportunity_score,
    opportunity_tier,
    coverage_status
FROM vw_market_opportunity
WHERE is_candidate = 1
ORDER BY opportunity_score DESC, relative_representation ASC, city_name
LIMIT 30;

-- QUERY: Q29 | Top candidate coverage gaps per city
-- Business question: What are the top three candidate gaps in each city,
-- using ROW_NUMBER to keep the list manageable?
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY city_id
            ORDER BY opportunity_score DESC, relative_representation ASC, category_name
        ) AS candidate_rank
    FROM vw_market_opportunity
    WHERE is_candidate = 1
)
SELECT
    city_name,
    category_name,
    listing_count,
    city_total,
    relative_representation,
    opportunity_score,
    opportunity_tier,
    candidate_rank
FROM ranked
WHERE candidate_rank <= 3
ORDER BY city_name, candidate_rank;

-- QUERY: Q30 | Coverage KPI summary
-- Business question: How much of the defined city-category universe is
-- covered, and how many high-tier candidate gaps exist?
SELECT
    COUNT(*) AS total_city_category_pairs,
    SUM(is_covered) AS covered_pairs,
    ROUND(100 * SUM(is_covered) / NULLIF(COUNT(*), 0), 2) AS category_coverage_pct,
    ROUND(AVG(listing_count), 2) AS avg_listings_per_city_category,
    SUM(is_candidate) AS candidate_pairs,
    SUM(CASE WHEN opportunity_tier = 'High' THEN 1 ELSE 0 END) AS high_tier_pairs,
    SUM(CASE WHEN opportunity_tier = 'Medium' THEN 1 ELSE 0 END) AS medium_tier_pairs
FROM vw_market_opportunity;

-- QUERY: Q31 | Supporting listing counts for opportunity review
-- Business question: What raw listing-count evidence supports the opportunity
-- ranking?
SELECT
    city_name,
    category_name,
    listing_count,
    city_total,
    category_total,
    category_share_in_city_pct,
    relative_representation,
    RANK() OVER (ORDER BY listing_count DESC) AS pair_count_rank
FROM vw_market_opportunity
ORDER BY listing_count DESC, city_name, category_name
LIMIT 50;

-- QUERY: Q32 | Quality status and band distribution
-- Business question: How many records fall into each validation and quality
-- band, and what share of the dataset do they represent?
SELECT
    validation_status,
    quality_band,
    COUNT(*) AS listing_count,
    ROUND(100 * COUNT(*) / (SELECT COUNT(*) FROM vw_listing_detail), 2) AS dataset_share_pct
FROM vw_listing_detail
GROUP BY validation_status, quality_band
ORDER BY validation_status, quality_band;

-- QUERY: Q33 | Collection snapshot
-- Business question: Is there a reliable time dimension for trend analysis?
SELECT
    collection_date,
    COUNT(*) AS listing_count,
    COUNT(DISTINCT city_id) AS cities_present,
    COUNT(DISTINCT source_id) AS sources_present
FROM listing_master
GROUP BY collection_date
ORDER BY collection_date;

-- QUERY: Q34 | Opportunity methodology parameters
-- Business question: Which weights and evidence thresholds produced the
-- opportunity score?
SELECT
    config_id,
    underrepresentation_weight,
    city_breadth_weight,
    reliability_weight,
    high_threshold,
    medium_threshold,
    min_city_listings,
    min_category_national_count,
    updated_at
FROM opportunity_config;

-- QUERY: Q35 | Category completeness by city (data-quality drill-down)
-- Business question: Which city-category cells have the weakest contact-data
-- completeness and therefore lower analytical reliability?
SELECT
    c.city_name,
    cat.category_name,
    COUNT(*) AS listing_count,
    ROUND(100 * SUM(CASE WHEN q.is_complete = 1 THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 2) AS completeness_pct,
    ROUND(100 * SUM(CASE WHEN q.missing_phone = 1 THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 2) AS missing_phone_pct,
    ROUND(100 * SUM(CASE WHEN q.missing_address = 1 THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 2) AS missing_address_pct
FROM listing_master l
JOIN dim_city c ON c.city_id = l.city_id
JOIN dim_category cat ON cat.category_id = l.category_id
JOIN data_quality_audit q ON q.listing_id = l.id
GROUP BY c.city_id, c.city_name, cat.category_id, cat.category_name
HAVING COUNT(*) >= 5
ORDER BY completeness_pct ASC, listing_count DESC
LIMIT 50;
