// Query name: DimCity
// Load: ON. Grain: one city. Source: dim_city.
//
// The latitude/longitude here are city centroids. The map page uses the
// listing coordinates from FactListings; these are for city-level tooltips or
// a separate centroid layer.

let
    Source = MySQL.Database(MySqlServer, MySqlDatabase),
    CityTable = Source{[Schema=MySqlDatabase, Item="dim_city"]}[Data],
    SelectedColumns = Table.SelectColumns(
        CityTable,
        {"city_id", "city_name", "state_name", "country", "latitude", "longitude"}
    ),
    TypedColumns = Table.TransformColumnTypes(
        SelectedColumns,
        {
            {"city_id", Int64.Type},
            {"city_name", type text},
            {"state_name", type text},
            {"country", type text},
            {"latitude", type number},
            {"longitude", type number}
        }
    )
in
    TypedColumns
