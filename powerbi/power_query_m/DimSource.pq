// Query name: DimSource
// Load: ON. Grain: one source. Source: dim_source.
//
// The dataset currently has one source. Source comparisons are not possible;
// the page uses this table for attribution and descriptive completeness only.

let
    Source = MySQL.Database(MySqlServer, MySqlDatabase),
    SourceTable = Source{[Schema=MySqlDatabase, Item="dim_source"]}[Data],
    SelectedColumns = Table.SelectColumns(
        SourceTable,
        {
            "source_id",
            "source_name",
            "source_type",
            "source_url",
            "license_name",
            "license_url",
            "attribution"
        }
    ),
    TypedColumns = Table.TransformColumnTypes(
        SelectedColumns,
        {
            {"source_id", Int64.Type},
            {"source_name", type text},
            {"source_type", type text},
            {"source_url", type text},
            {"license_name", type text},
            {"license_url", type text},
            {"attribution", type text}
        }
    )
in
    TypedColumns
