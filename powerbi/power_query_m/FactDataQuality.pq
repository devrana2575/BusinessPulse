// Query name: FactDataQuality
// Load: ON. Grain: one row per listing.
// Source: references stg_Listings (itself from vw_listing_detail).
//
// Deliberately excludes city_id/category_id: filters reach this table through
// the 1:1 relationship from FactListings. Adding those IDs would create a
// second filter path and ambiguous relationships.
//
// Flags are whole numbers (0/1). They are not booleans in MySQL.

let
    Source = stg_Listings,
    SelectedColumns = Table.SelectColumns(
        Source,
        {
            "listing_id",
            "missing_phone",
            "missing_address",
            "duplicate_flag",
            "potential_duplicate_flag",
            "phone_valid",
            "address_valid",
            "is_complete",
            "validation_status",
            "quality_score",
            "quality_band"
        }
    )
in
    SelectedColumns
