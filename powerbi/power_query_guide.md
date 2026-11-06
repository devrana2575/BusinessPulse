# BusinessPulse — Power Query connection guide

## Status

**IMPLEMENTED AS SOURCE FILES — NOT VERIFIED IN POWER BI DESKTOP.** Power BI
Desktop is installed from the Microsoft Store (version 2.159.883.0), but these
queries have not yet been executed there. Verify the MySQL Connector/NET
prerequisite, follow these steps in Desktop, and record actual results.

## Prerequisites

- Power BI Desktop for Windows, version 2.159.883.0 in the inspected
  environment.
- MySQL Connector/NET (the Power BI MySQL connector depends on it). Install the
  current MySQL Connector/NET and restart Desktop.
- A reachable MySQL 8+/9.x instance with the `businesspulse` database loaded.
- Network access from the Desktop machine to MySQL; for this project, local
  development used `127.0.0.1:3307`.

## Parameters

In **Home → Manage Parameters → New Parameter**, create:

| Name | Type | Suggested value | Notes |
|---|---|---|---|
| `MySqlServer` | Text | `127.0.0.1:3306` | Use `host:port`. For the local build, `127.0.0.1:3307` was used. |
| `MySqlDatabase` | Text | `businesspulse` | The reporting database. |

Do not commit credentials. Power BI stores connection credentials in its own
credential store, not in these files. The database user needs `SELECT` on the
views/tables only.

## Connection

1. **Get data → MySQL database**.
2. Server: `MySqlServer`; Database: `MySqlDatabase`.
3. Choose **Import** (not DirectQuery).
4. On the credentials prompt, select **Database** and enter the application
   user (not the MySQL root account).
5. If Desktop warns about an untrusted certificate on a local instance, review
   the connection setting with your environment owner. Do not disable
   certificate validation on a shared or production server.

The M files use:

```m
MySQL.Database(MySqlServer, MySqlDatabase)
```

and navigate with:

```m
Source{[Schema=MySqlDatabase, Item="vw_listing_detail"]}[Data]
```

If your MySQL provider returns a case-sensitive schema or a different
navigation shape, use the Navigator UI to select the view once, then copy the
generated navigation expression. Record any deviation.

## Query load order

Create the queries in this order so references resolve:

1. `stg_Listings`
2. `FactListings` (references `stg_Listings`)
3. `FactDataQuality` (references `stg_Listings`)
4. `DimCity`
5. `DimCategory`
6. `DimSource`
7. `FactCityCategoryCoverage`

`stg_Listings` must have **Include in report refresh** on but **Enable load**
off. It is a staging query, not a report table.

## Column types

The `.pq` files already declare types. After the first refresh, confirm:

- `collection_date` is Date.
- `latitude` and `longitude` are Decimal Number.
- `quality_score` and opportunity score columns are Decimal Number.
- All flag columns are Whole Number.
- IDs are Whole Number (or Text if your MySQL provider returns them as text).
- `business_name`, `city_name`, `category_name`, `source_name` are Text.

If MySQL `DECIMAL` values arrive as `type any`, change them with **Transform
Column → Data Type → Decimal Number** and refresh.

## Refresh procedure

```powershell
# Only after approving and verifying the explicit empty target
python scripts/businesspulse.py import --database businesspulse --confirm-target-empty
```

Do not use `--replace-data` on an existing database without explicit approval;
that option deletes existing listing, audit, reject and batch rows.

Then in Power BI Desktop:

1. **Home → Refresh**.
2. Check the manual validation table in `powerbi/README.md`.
3. Save the PBIX.
4. Re-capture screenshots if the numbers changed.

Do not refresh the PBIX while the Python import transaction is still running.
The import is transactional, so a refresh sees either the old committed state
or the new committed state.

## Common errors and honest resolutions

| Error | Likely cause | Resolution |
|---|---|---|
| `MySQL: We couldn't authenticate` | Wrong user/password, or user lacks access from this host | Verify `bp_user` grants for the database; never use root in the report. |
| `The specified module could not be found` | MySQL Connector/NET missing | Install Connector/NET, restart Desktop. |
| `Table not found` | Schema/database mismatch or setup not run | Verify the intended target is empty and approved, then provision it without `--reset`; never use reset on an existing database. |
| `Expression.Error: The key didn't match any rows` | View name changed or database wrong | Re-check Navigator and the `Item` name in the query. |
| Slow refresh | Import mode, but large views/complex joins on a small machine | Check indexes, refresh outside report use. The dataset is small. |
| Relationship creates ambiguity | Added a direct city/category relationship to `FactDataQuality` | Follow `data_model.md`; route filters through `FactListings`. |

## What is not automated

- Power BI credentials, refresh schedule, gateway, workspace publishing.
- `.pbix` creation and screenshot capture.
- Power BI-specific DAX validation and accessibility checks.

These are deliberately marked **PENDING MANUAL ACTION**, not claimed as done.
