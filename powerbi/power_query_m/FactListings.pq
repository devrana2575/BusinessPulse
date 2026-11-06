// Query name: FactListings
// Load: ON. Grain: one collected listing.
// Source: references stg_Listings (itself from vw_listing_detail).
//
// City/category/source IDs are hidden in the model and related to dimensions.
// Contact fields remain public business contact data; do not add private data.

let
    Source = stg_Listings,
    SelectedColumns = Table.SelectColumns(
        Source,
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
            "longitude"
        }
    )
in
    SelectedColumns
