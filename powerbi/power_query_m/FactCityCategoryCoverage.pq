// Query name: FactCityCategoryCoverage
// Load: ON. Grain: one city x category pair (cities with >=1 listing x 12).
// Source: vw_market_opportunity.
//
// The view already applies the documented score, candidate rule and tiers.
// Do not recompute the score in Power Query; keep one formula in SQL/Python.
// Do not sum the opportunity score across pairs. Use the DAX average/MAXX
// measures and label them as descriptive.

let
    Source = MySQL.Database(MySqlServer, MySqlDatabase),
    OpportunityView = Source{[Schema=MySqlDatabase, Item="vw_market_opportunity"]}[Data],
    SelectedColumns = Table.SelectColumns(
        OpportunityView,
        {
            "city_id",
            "city_name",
            "state_name",
            "category_id",
            "category_name",
            "listing_count",
            "city_total",
            "category_total",
            "total_listings",
            "category_share_in_city_pct",
            "national_category_share_pct",
            "relative_representation",
            "is_covered",
            "categories_present",
            "total_categories",
            "city_category_coverage_pct",
            "city_completeness_pct",
            "city_avg_quality_score",
            "is_candidate",
            "coverage_status",
            "underrepresentation_index",
            "city_breadth_gap",
            "reliability_index",
            "underrepresentation_points",
            "breadth_points",
            "reliability_points",
            "opportunity_score",
            "opportunity_tier",
            "underrepresentation_weight",
            "city_breadth_weight",
            "reliability_weight",
            "high_threshold",
            "medium_threshold",
            "methodology_note"
        }
    ),
    TypedColumns = Table.TransformColumnTypes(
        SelectedColumns,
        {
            {"city_id", Int64.Type},
            {"city_name", type text},
            {"state_name", type text},
            {"category_id", Int64.Type},
            {"category_name", type text},
            {"listing_count", Int64.Type},
            {"city_total", Int64.Type},
            {"category_total", Int64.Type},
            {"total_listings", Int64.Type},
            {"category_share_in_city_pct", type number},
            {"national_category_share_pct", type number},
            {"relative_representation", type number},
            {"is_covered", Int64.Type},
            {"categories_present", Int64.Type},
            {"total_categories", Int64.Type},
            {"city_category_coverage_pct", type number},
            {"city_completeness_pct", type number},
            {"city_avg_quality_score", type number},
            {"is_candidate", Int64.Type},
            {"coverage_status", type text},
            {"underrepresentation_index", type number},
            {"city_breadth_gap", type number},
            {"reliability_index", type number},
            {"underrepresentation_points", type number},
            {"breadth_points", type number},
            {"reliability_points", type number},
            {"opportunity_score", type number},
            {"opportunity_tier", type text},
            {"underrepresentation_weight", type number},
            {"city_breadth_weight", type number},
            {"reliability_weight", type number},
            {"high_threshold", type number},
            {"medium_threshold", type number},
            {"methodology_note", type text}
        }
    )
in
    TypedColumns
