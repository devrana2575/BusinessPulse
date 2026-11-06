// Query name: stg_Listings
// Load: OFF (staging only). Include in report refresh: ON.
// Source: vw_listing_detail, grain = one collected listing.
//
// This query selects and types every column once. FactListings and
// FactDataQuality both reference this query, so the source contract is kept in
// one place. No missing phone/address is imputed.

let
    Source = MySQL.Database(MySqlServer, MySqlDatabase),
    ListingView = Source{[Schema=MySqlDatabase, Item="vw_listing_detail"]}[Data],
    SelectedColumns = Table.SelectColumns(
        ListingView,
        {
            "listing_id",
            "business_id",
            "business_name",
            "city_id",
            "category_id",
            "source_id",
            "address",
            "phone",
            "source_record_id",
            "collection_date",
            "latitude",
            "longitude",
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
    ),
    TypedColumns = Table.TransformColumnTypes(
        SelectedColumns,
        {
            {"listing_id", Int64.Type},
            {"business_id", type text},
            {"business_name", type text},
            {"city_id", Int64.Type},
            {"category_id", Int64.Type},
            {"source_id", Int64.Type},
            {"address", type text},
            {"phone", type text},
            {"source_record_id", type text},
            {"collection_date", type date},
            {"latitude", type number},
            {"longitude", type number},
            {"missing_phone", Int64.Type},
            {"missing_address", Int64.Type},
            {"duplicate_flag", Int64.Type},
            {"potential_duplicate_flag", Int64.Type},
            {"phone_valid", Int64.Type},
            {"address_valid", Int64.Type},
            {"is_complete", Int64.Type},
            {"validation_status", type text},
            {"quality_score", type number},
            {"quality_band", type text}
        }
    ),
    FilteredRows = Table.SelectRows(TypedColumns, each [listing_id] <> null)
in
    FilteredRows
