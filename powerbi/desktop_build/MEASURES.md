# BusinessPulse - measure reference

50 measures. **Expected values are an independent pandas reference computed from the exported CSVs; DAX has not yet been evaluated in Power BI Desktop.** Record the Desktop result next to each expected value in `VALIDATION_REPORT.md`.

Format strings: set in Measure tools > Format.

## 01 Volume

### Total Listings

```dax
Total Listings =
    COUNTROWS ( FactListings )
```

- **Calculation:** Counts listing rows in the current filter context.
- **Source columns:** FactListings (rows)
- **Format:** `#,0`
- **Validate:** 2,252 with no filters. Must equal row count of FactListings.csv.

### Unique Businesses

```dax
Unique Businesses =
    DISTINCTCOUNT ( FactListings[business_id] )
```

- **Calculation:** Distinct business IDs; proves no duplicated keys in the fact.
- **Source columns:** FactListings[business_id]
- **Format:** `#,0`
- **Validate:** 2,252. Must equal [Total Listings] (3 exact duplicates are flagged but retained with distinct IDs).

### Total Cities

```dax
Total Cities =
    DISTINCTCOUNT ( FactListings[city_id] )
```

- **Calculation:** Cities that have at least one listing in context (not rows in DimCity).
- **Source columns:** FactListings[city_id]
- **Format:** `0`
- **Validate:** 12 unfiltered; 1 when one city is selected.

### Total Categories

```dax
Total Categories =
    DISTINCTCOUNT ( FactListings[category_id] )
```

- **Calculation:** Categories with at least one listing in context.
- **Source columns:** FactListings[category_id]
- **Format:** `0`
- **Validate:** 12 unfiltered; Hyderabad = 9.

### Avg Listings per City

```dax
Avg Listings per City =
    DIVIDE ( [Total Listings], [Total Cities] )
```

- **Calculation:** Mean listings per represented city. Descriptive only: counts are capped by the collection design.
- **Source columns:** FactListings
- **Format:** `#,0.0`
- **Validate:** 187.67 (2,252 / 12). Do not sum.

### Listing Share %

```dax
Listing Share % =
    DIVIDE (
        [Total Listings],
        CALCULATE ( [Total Listings], ALLSELECTED ( DimCity ), ALLSELECTED ( DimCategory ) )
    )
```

- **Calculation:** Share of listings within whatever the slicers currently select. Use on a city or category axis.
- **Source columns:** FactListings; DimCity; DimCategory
- **Format:** `0.0%`
- **Validate:** By city: Surat 9.15% (max). By category: Retail 20.07%. Axis values sum to 100%.

### Snapshot Date

```dax
Snapshot Date =
    MAX ( FactListings[collection_date] )
```

- **Calculation:** Collection date of the snapshot (single date, so no date slicer or Date table is needed).
- **Source columns:** FactListings[collection_date] (Date)
- **Format:** `dd mmm yyyy`
- **Validate:** 2 Nov 2026.

### Largest City Listings

```dax
Largest City Listings =
    MAXX ( ALLSELECTED ( DimCity ), [Total Listings] )
```

- **Calculation:** Listings of the largest selected city.
- **Source columns:** DimCity; FactListings
- **Format:** `#,0`
- **Validate:** 206 (Surat).

### Smallest City Listings

```dax
Smallest City Listings =
    MINX ( ALLSELECTED ( DimCity ), [Total Listings] )
```

- **Calculation:** Listings of the smallest selected city.
- **Source columns:** DimCity; FactListings
- **Format:** `#,0`
- **Validate:** 174 (Delhi).

### City Rank

```dax
City Rank =
    RANKX ( ALLSELECTED ( DimCity[city_name] ), [Total Listings], , DESC, DENSE )
```

- **Calculation:** Dense rank of a city by listings among selected cities.
- **Source columns:** DimCity[city_name]
- **Format:** `0`
- **Validate:** Surat = 1, Chennai = 2, Delhi = 12.

## 02 Concentration & Coverage

### Top City Share %

```dax
Top City Share % =
    DIVIDE (
        MAXX ( ALLSELECTED ( DimCity ), [Total Listings] ),
        CALCULATE ( [Total Listings], ALLSELECTED ( DimCity ) )
    )
```

- **Calculation:** Largest city's share of selected listings. A collection-design indicator, not market concentration.
- **Source columns:** DimCity; FactListings
- **Format:** `0.00%`
- **Validate:** 9.15%.

### City HHI

```dax
City HHI =
    VAR _total = CALCULATE ( [Total Listings], ALLSELECTED ( DimCity ) )
    RETURN
        SUMX ( ALLSELECTED ( DimCity ), POWER ( DIVIDE ( [Total Listings], _total ), 2 ) )
```

- **Calculation:** Herfindahl-Hirschman index of city shares (0-1). 1/12 = 0.0833 is perfectly even.
- **Source columns:** DimCity; FactListings
- **Format:** `0.0000`
- **Validate:** 0.0835 (near-even; reflects capped collection).

### Category Coverage %

```dax
Category Coverage % =
    DIVIDE (
        DISTINCTCOUNT ( FactListings[category_id] ),
        CALCULATE ( COUNTROWS ( DimCategory ), ALL ( DimCategory ) )
    )
```

- **Calculation:** Share of the 12 categories present. Use on a city axis (categories present / 12).
- **Source columns:** FactListings[category_id]; DimCategory
- **Format:** `0.0%`
- **Validate:** 100% unfiltered; Hyderabad 75.0%; Surat 83.3%. Do not use on a category axis.

### City Coverage %

```dax
City Coverage % =
    DIVIDE (
        DISTINCTCOUNT ( FactListings[city_id] ),
        CALCULATE ( COUNTROWS ( DimCity ), ALL ( DimCity ) )
    )
```

- **Calculation:** Share of the 12 cities that have the category. Use on a category axis.
- **Source columns:** FactListings[city_id]; DimCity
- **Format:** `0.0%`
- **Validate:** 100% unfiltered; Education & Training 16.7% (2 cities).

### Total Pairs

```dax
Total Pairs =
    COUNTROWS ( FactCityCategoryCoverage )
```

- **Calculation:** City x category combinations in context.
- **Source columns:** FactCityCategoryCoverage
- **Format:** `0`
- **Validate:** 144.

### Covered Pairs

```dax
Covered Pairs =
    SUM ( FactCityCategoryCoverage[is_covered] )
```

- **Calculation:** Pairs with at least one collected listing.
- **Source columns:** FactCityCategoryCoverage[is_covered]
- **Format:** `0`
- **Validate:** 123.

### Uncovered Pairs

```dax
Uncovered Pairs =
    [Total Pairs] - [Covered Pairs]
```

- **Calculation:** Pairs with zero collected listings (collected-data gaps).
- **Source columns:** FactCityCategoryCoverage
- **Format:** `0`
- **Validate:** 21.

### Pair Coverage %

```dax
Pair Coverage % =
    DIVIDE ( [Covered Pairs], [Total Pairs] )
```

- **Calculation:** Covered / possible pairs; respects city and category slicers.
- **Source columns:** FactCityCategoryCoverage
- **Format:** `0.0%`
- **Validate:** 85.42% (matches Q30 coverage_pct).

### Pair Listings

```dax
Pair Listings =
    SUM ( FactCityCategoryCoverage[listing_count] )
```

- **Calculation:** Listings summed over pairs; reconciles the coverage fact to the listing fact.
- **Source columns:** FactCityCategoryCoverage[listing_count]
- **Format:** `#,0`
- **Validate:** 2,252. Must equal [Total Listings] at any slicer state.

### Missing Categories

```dax
Missing Categories =
    CONCATENATEX (
        FILTER ( ALL ( DimCategory[category_name] ), CALCULATE ( [Total Listings] ) = 0 ),
        DimCategory[category_name], ", ", DimCategory[category_name], ASC
    )
```

- **Calculation:** Comma-separated categories with zero listings in the current (city) context. Tooltip/table use.
- **Source columns:** DimCategory[category_name]; FactListings
- **Format:** `text`
- **Validate:** Hyderabad -> Beauty & Personal Care, Education & Training, Professional Services (3 missing).

## 03 Data Quality

### Duplicate Count

```dax
Duplicate Count =
    SUM ( FactListings[duplicate_flag] )
```

- **Calculation:** Exact duplicates flagged by cleaning (name + city + address); retained, not deleted.
- **Source columns:** FactListings[duplicate_flag]
- **Format:** `0`
- **Validate:** 3 (Ahmedabad 2, Surat 1).

### Missing Phone Count

```dax
Missing Phone Count =
    SUM ( FactListings[missing_phone] )
```

- **Calculation:** Listings with no published phone.
- **Source columns:** FactListings[missing_phone]
- **Format:** `#,0`
- **Validate:** 2,088.

### Missing Address Count

```dax
Missing Address Count =
    SUM ( FactListings[missing_address] )
```

- **Calculation:** Listings with no published address.
- **Source columns:** FactListings[missing_address]
- **Format:** `#,0`
- **Validate:** 1,615.

### Missing Phone %

```dax
Missing Phone % =
    DIVIDE ( [Missing Phone Count], [Total Listings] )
```

- **Calculation:** Share of listings with no phone.
- **Source columns:** FactListings
- **Format:** `0.0%`
- **Validate:** 92.72%.

### Missing Address %

```dax
Missing Address % =
    DIVIDE ( [Missing Address Count], [Total Listings] )
```

- **Calculation:** Share of listings with no address.
- **Source columns:** FactListings
- **Format:** `0.0%`
- **Validate:** 71.71%.

### Invalid Phone Count

```dax
Invalid Phone Count =
    SUM ( FactListings[invalid_phone] )
```

- **Calculation:** Phone present but outside the project's 7-15 digit rule.
- **Source columns:** FactListings[invalid_phone]
- **Format:** `0`
- **Validate:** 5.

### Invalid Address Count

```dax
Invalid Address Count =
    SUM ( FactListings[invalid_address] )
```

- **Calculation:** Address present but too short/unstructured per the cleaning rule.
- **Source columns:** FactListings[invalid_address]
- **Format:** `0`
- **Validate:** 54.

### Missing Coordinate Count

```dax
Missing Coordinate Count =
    COUNTROWS (
        FILTER ( FactListings, ISBLANK ( FactListings[latitude] ) || ISBLANK ( FactListings[longitude] ) )
    )
```

- **Calculation:** Listings with a blank latitude or longitude.
- **Source columns:** FactListings[latitude], [longitude]
- **Format:** `0`
- **Validate:** 0 (raw build reports missing_coordinates = 0).

### Invalid Coordinate Count

```dax
Invalid Coordinate Count =
    SUM ( FactListings[invalid_coordinate] )
```

- **Calculation:** Blank or outside lat -90..90 / lon -180..180 (identical to the cleaning.py rule).
- **Source columns:** FactListings[invalid_coordinate]
- **Format:** `0`
- **Validate:** 0 - a true zero, not a missing metric.

### Outside City Bbox Count

```dax
Outside City Bbox Count =
    SUM ( FactListings[outside_city_bbox] )
```

- **Calculation:** Coordinates outside the city's collection bounding box (project constants). Derived sanity check.
- **Source columns:** FactListings[outside_city_bbox]
- **Format:** `0`
- **Validate:** 0.

### Missing Business Name Count

```dax
Missing Business Name Count =
    COUNTROWS (
        FILTER ( FactListings, ISBLANK ( FactListings[business_name] ) || TRIM ( FactListings[business_name] ) = "" )
    )
```

- **Calculation:** Blank business names.
- **Source columns:** FactListings[business_name]
- **Format:** `0`
- **Validate:** 0 (unnamed OSM elements were excluded at collection: 233).

### Missing Category Count

```dax
Missing Category Count =
    COUNTROWS ( FILTER ( FactListings, ISBLANK ( FactListings[category_id] ) ) )
```

- **Calculation:** Listings with no category key.
- **Source columns:** FactListings[category_id]
- **Format:** `0`
- **Validate:** 0.

### Quality Issue Rows

```dax
Quality Issue Rows =
    COUNTROWS ( FactQualityIssues )
```

- **Calculation:** Audit warnings (one row per field issue). A listing can have several.
- **Source columns:** FactQualityIssues
- **Format:** `#,0`
- **Validate:** 3,762 = 2,088 + 1,615 + 54 + 5.

### Data Quality Issue Count

```dax
Data Quality Issue Count =
    [Quality Issue Rows] + [Duplicate Count] + [Invalid Coordinate Count]
```

- **Calculation:** Audit warnings plus duplicate and coordinate flags (duplicates are not in the issue table).
- **Source columns:** FactQualityIssues; FactListings
- **Format:** `#,0`
- **Validate:** 3,765 (3,762 + 3 + 0).

### Needs Review Records

```dax
Needs Review Records =
    CALCULATE ( [Total Listings], FactListings[validation_status] = "needs_review" )
```

- **Calculation:** Listings failing at least one audit rule.
- **Source columns:** FactListings[validation_status]
- **Format:** `#,0`
- **Validate:** 2,123.

### Complete Records

```dax
Complete Records =
    SUM ( FactListings[is_complete] )
```

- **Calculation:** Valid phone AND valid address AND not an exact duplicate.
- **Source columns:** FactListings[is_complete]
- **Format:** `#,0`
- **Validate:** 129.

### Complete Records %

```dax
Complete Records % =
    DIVIDE ( [Complete Records], [Total Listings] )
```

- **Calculation:** Strict completeness rate.
- **Source columns:** FactListings
- **Format:** `0.0%`
- **Validate:** 5.73%.

### Avg Quality Score

```dax
Avg Quality Score =
    AVERAGE ( FactListings[quality_score] )
```

- **Calculation:** Mean of the project's documented 0-100 score (100 minus penalties for missing/invalid phone and address and duplicates).
- **Source columns:** FactListings[quality_score]
- **Format:** `0.0`
- **Validate:** 63.36.

### Data Quality %

```dax
Data Quality % =
    DIVIDE ( [Avg Quality Score], 100 )
```

- **Calculation:** Avg Quality Score expressed as a percentage. Not the same as completeness.
- **Source columns:** FactListings[quality_score]
- **Format:** `0.0%`
- **Validate:** 63.36%.

## 04 Opportunity

### Candidate Pairs

```dax
Candidate Pairs =
    SUM ( FactCityCategoryCoverage[is_candidate] )
```

- **Calculation:** Pairs passing the project's evidence rule (city >= 20 listings and category >= 5 nationally).
- **Source columns:** FactCityCategoryCoverage[is_candidate]
- **Format:** `0`
- **Validate:** 132 (144 - 12 Education & Training pairs).

### High Opportunity Pairs

```dax
High Opportunity Pairs =
    CALCULATE ( COUNTROWS ( FactCityCategoryCoverage ), FactCityCategoryCoverage[opportunity_tier] = "High" )
```

- **Calculation:** Pairs scoring >= 60 (project threshold).
- **Source columns:** FactCityCategoryCoverage[opportunity_tier]
- **Format:** `0`
- **Validate:** 12.

### Medium Opportunity Pairs

```dax
Medium Opportunity Pairs =
    CALCULATE ( COUNTROWS ( FactCityCategoryCoverage ), FactCityCategoryCoverage[opportunity_tier] = "Medium" )
```

- **Calculation:** Pairs scoring 40-<60.
- **Source columns:** FactCityCategoryCoverage[opportunity_tier]
- **Format:** `0`
- **Validate:** 5.

### Opportunity Count

```dax
Opportunity Count =
    [High Opportunity Pairs] + [Medium Opportunity Pairs]
```

- **Calculation:** Pairs flagged High or Medium: a review shortlist, not proven demand.
- **Source columns:** FactCityCategoryCoverage
- **Format:** `0`
- **Validate:** 17.

### Avg Opportunity Score

```dax
Avg Opportunity Score =
    CALCULATE ( AVERAGE ( FactCityCategoryCoverage[opportunity_score] ), FactCityCategoryCoverage[is_candidate] = 1 )
```

- **Calculation:** Mean score over candidate pairs only. Descriptive; never sum scores.
- **Source columns:** FactCityCategoryCoverage[opportunity_score], [is_candidate]
- **Format:** `0.0`
- **Validate:** 15.83.

### Highest Opportunity Score

```dax
Highest Opportunity Score =
    CALCULATE ( MAX ( FactCityCategoryCoverage[opportunity_score] ), FactCityCategoryCoverage[is_candidate] = 1 )
```

- **Calculation:** Top candidate score.
- **Source columns:** FactCityCategoryCoverage[opportunity_score], [is_candidate]
- **Format:** `0.00`
- **Validate:** 66.92 (Chandigarh - Other Services / Home & Repair Services).

### Opportunity Score (Pair)

```dax
Opportunity Score (Pair) =
    IF ( MAX ( FactCityCategoryCoverage[is_candidate] ) = 1, MAX ( FactCityCategoryCoverage[opportunity_score] ) )
```

- **Calculation:** Score for one city x category cell; BLANK for insufficient-evidence pairs so they are not shown as scored.
- **Source columns:** FactCityCategoryCoverage[opportunity_score], [is_candidate]
- **Format:** `0.0`
- **Validate:** Education & Training cells are blank in every city.

### Relative Representation (Pair)

```dax
Relative Representation (Pair) =
    IF ( COUNTROWS ( FactCityCategoryCoverage ) = 1, MAX ( FactCityCategoryCoverage[relative_representation] ) )
```

- **Calculation:** City category share / national category share for one pair (1.0 = at baseline).
- **Source columns:** FactCityCategoryCoverage[relative_representation]
- **Format:** `0.00`
- **Validate:** Pune - Retail = 1.038; Pune - Professional Services = 0.378.

### Avg Underrepresentation Points

```dax
Avg Underrepresentation Points =
    CALCULATE ( AVERAGE ( FactCityCategoryCoverage[underrepresentation_points] ), FactCityCategoryCoverage[is_candidate] = 1 )
```

- **Calculation:** Score component (weight 0.60). At pair level equals the stored value.
- **Source columns:** FactCityCategoryCoverage[underrepresentation_points]
- **Format:** `0.00`
- **Validate:** Pune - Professional Services = 37.30.

### Avg Breadth Points

```dax
Avg Breadth Points =
    CALCULATE ( AVERAGE ( FactCityCategoryCoverage[breadth_points] ), FactCityCategoryCoverage[is_candidate] = 1 )
```

- **Calculation:** Score component (weight 0.25): city category breadth gap.
- **Source columns:** FactCityCategoryCoverage[breadth_points]
- **Format:** `0.00`
- **Validate:** Pune = 2.08.

### Avg Reliability Points

```dax
Avg Reliability Points =
    CALCULATE ( AVERAGE ( FactCityCategoryCoverage[reliability_points] ), FactCityCategoryCoverage[is_candidate] = 1 )
```

- **Calculation:** Score component (weight 0.15): city completeness. Higher completeness raises the score (a confidence term).
- **Source columns:** FactCityCategoryCoverage[reliability_points]
- **Format:** `0.00`
- **Validate:** Pune = 0.78. Three components sum to the pair score (+-0.01).
