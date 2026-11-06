// Query name: DimCategory
// Load: ON. Grain: one of 12 analytical categories. Source: dim_category.
//
// In Model view, sort category_name by display_order and hide display_order.

let
    Source = MySQL.Database(MySqlServer, MySqlDatabase),
    CategoryTable = Source{[Schema=MySqlDatabase, Item="dim_category"]}[Data],
    SelectedColumns = Table.SelectColumns(
        CategoryTable,
        {"category_id", "category_name", "display_order", "description"}
    ),
    TypedColumns = Table.TransformColumnTypes(
        SelectedColumns,
        {
            {"category_id", Int64.Type},
            {"category_name", type text},
            {"display_order", Int64.Type},
            {"description", type text}
        }
    )
in
    TypedColumns
