// =============================================================================
// BusinessPulse - Power Query (M) for the Desktop build. Paste each query into
// Home > Transform data > New Source > Blank Query > Advanced Editor, and rename it
// to the name in the first comment line. Create the DataFolder parameter FIRST.
// Culture is fixed to en-US so decimals parse identically on any Windows region.
// =============================================================================

// ---------- Parameter: DataFolder (Home > Manage Parameters > New Parameter) ----------
// Name: DataFolder | Type: Text | Required | Current value must END with a backslash, e.g.
// C:\Users\YOU\BusinessPulse-master\powerbi\desktop_build\data\
"C:\Users\YOU\BusinessPulse-master\powerbi\desktop_build\data\" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]

// ---------- Query name: DimCity ----------
// One row per city. Centroid/bbox come from the project's CITY_METADATA (same values as seed_data.sql).
let
    Source = Csv.Document(File.Contents(DataFolder & "DimCity.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(
        Promoted,
        {
            {"city_id", Int64.Type},
            {"city_name", type text},
            {"state_name", type text},
            {"centroid_latitude", type number},
            {"centroid_longitude", type number},
            {"bbox_south", type number},
            {"bbox_west", type number},
            {"bbox_north", type number},
            {"bbox_east", type number}
        },
        "en-US"
    )
in
    Typed

// ---------- Query name: DimCategory ----------
// One row per category. After load: sort category_name by display_order, then hide display_order.
let
    Source = Csv.Document(File.Contents(DataFolder & "DimCategory.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(
        Promoted,
        {
            {"category_id", Int64.Type},
            {"category_name", type text},
            {"display_order", Int64.Type},
            {"description", type text}
        },
        "en-US"
    )
in
    Typed

// ---------- Query name: DimSource ----------
// One row: OpenStreetMap (Overpass API). Keeps ODbL licence and attribution visible in the model.
let
    Source = Csv.Document(File.Contents(DataFolder & "DimSource.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(
        Promoted,
        {
            {"source_id", Int64.Type},
            {"source_name", type text},
            {"source_type", type text},
            {"source_url", type text},
            {"license_name", type text},
            {"license_url", type text},
            {"attribution", type text}
        },
        "en-US"
    )
in
    Typed

// ---------- Query name: FactListings ----------
// One row per collected listing (2,252). Flags are 0/1 whole numbers.
let
    Source = Csv.Document(File.Contents(DataFolder & "FactListings.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(
        Promoted,
        {
            {"business_id", type text},
            {"business_name", type text},
            {"city_id", Int64.Type},
            {"category_id", Int64.Type},
            {"source_id", Int64.Type},
            {"address", type text},
            {"latitude", type number},
            {"longitude", type number},
            {"collection_date", type date},
            {"source_record_url", type text},
            {"missing_phone", Int64.Type},
            {"missing_address", Int64.Type},
            {"invalid_phone", Int64.Type},
            {"invalid_address", Int64.Type},
            {"duplicate_flag", Int64.Type},
            {"invalid_coordinate", Int64.Type},
            {"outside_city_bbox", Int64.Type},
            {"is_complete", Int64.Type},
            {"quality_score", Int64.Type},
            {"quality_band", type text},
            {"quality_band_sort", Int64.Type},
            {"validation_status", type text}
        },
        "en-US"
    )
in
    Typed

// ---------- Query name: FactQualityIssues ----------
// One row per audit warning from validation_issues.csv (3,762); joins to FactListings by business_id.
let
    Source = Csv.Document(File.Contents(DataFolder & "FactQualityIssues.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(
        Promoted,
        {
            {"issue_id", Int64.Type},
            {"business_id", type text},
            {"field", type text},
            {"issue_type", type text},
            {"severity", type text}
        },
        "en-US"
    )
in
    Typed

// ---------- Query name: FactCityCategoryCoverage ----------
// One row per city x category (144) from the SQL view output; score logic is NOT recomputed here.
let
    Source = Csv.Document(File.Contents(DataFolder & "FactCityCategoryCoverage.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(
        Promoted,
        {
            {"city_id", Int64.Type},
            {"category_id", Int64.Type},
            {"listing_count", Int64.Type},
            {"city_total", Int64.Type},
            {"category_total", Int64.Type},
            {"category_share_in_city_pct", type number},
            {"national_category_share_pct", type number},
            {"relative_representation", type number},
            {"is_covered", Int64.Type},
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
            {"opportunity_tier_sort", Int64.Type}
        },
        "en-US"
    )
in
    Typed
