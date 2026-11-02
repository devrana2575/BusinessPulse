# BusinessPulse - SQL / Python Reconciliation Report

Generated: 2026-11-02T17:10:41+00:00

- Checks: 37
- Passed: 37
- Failed: 0

The comparison is between Pandas over the cleaned CSV and the MySQL
reporting views. Power BI is not installed in this environment; its
critical values are listed in the manual verification checklist.

| Metric | Python | SQL | Difference | Tolerance | Status |
|---|---:|---:|---:|---:|---|
| total_listings | 2252.0 | 2252.0 | 0.0 | 0.0 | PASS |
| missing_phone_count | 2088.0 | 2088.0 | 0.0 | 0.0 | PASS |
| missing_phone_pct | 92.72 | 92.72 | 0.0 | 0.05 | PASS |
| missing_address_count | 1615.0 | 1615.0 | 0.0 | 0.0 | PASS |
| missing_address_pct | 71.71 | 71.71 | 0.0 | 0.05 | PASS |
| duplicate_count | 3.0 | 3.0 | 0.0 | 0.0 | PASS |
| duplicate_rate_pct | 0.13 | 0.13 | 0.0 | 0.05 | PASS |
| complete_listings | 129.0 | 129.0 | 0.0 | 0.0 | PASS |
| completeness_pct | 5.73 | 5.73 | 0.0 | 0.05 | PASS |
| avg_quality_score | 63.36 | 63.36 | 0.0 | 0.02 | PASS |
| city_listing_count::Ahmedabad | 192.0 | 192.0 | 0.0 | 0.0 | PASS |
| city_listing_count::Bengaluru | 190.0 | 190.0 | 0.0 | 0.0 | PASS |
| city_listing_count::Chandigarh | 179.0 | 179.0 | 0.0 | 0.0 | PASS |
| city_listing_count::Chennai | 201.0 | 201.0 | 0.0 | 0.0 | PASS |
| city_listing_count::Delhi | 174.0 | 174.0 | 0.0 | 0.0 | PASS |
| city_listing_count::Hyderabad | 186.0 | 186.0 | 0.0 | 0.0 | PASS |
| city_listing_count::Jaipur | 189.0 | 189.0 | 0.0 | 0.0 | PASS |
| city_listing_count::Kolkata | 182.0 | 182.0 | 0.0 | 0.0 | PASS |
| city_listing_count::Lucknow | 176.0 | 176.0 | 0.0 | 0.0 | PASS |
| city_listing_count::Mumbai | 185.0 | 185.0 | 0.0 | 0.0 | PASS |
| city_listing_count::Pune | 192.0 | 192.0 | 0.0 | 0.0 | PASS |
| city_listing_count::Surat | 206.0 | 206.0 | 0.0 | 0.0 | PASS |
| category_listing_count::Automotive | 351.0 | 351.0 | 0.0 | 0.0 | PASS |
| category_listing_count::Beauty & Personal Care | 42.0 | 42.0 | 0.0 | 0.0 | PASS |
| category_listing_count::Education & Training | 2.0 | 2.0 | 0.0 | 0.0 | PASS |
| category_listing_count::Finance & Banking | 224.0 | 224.0 | 0.0 | 0.0 | PASS |
| category_listing_count::Fitness & Recreation | 124.0 | 124.0 | 0.0 | 0.0 | PASS |
| category_listing_count::Food & Beverage | 447.0 | 447.0 | 0.0 | 0.0 | PASS |
| category_listing_count::Health & Pharmacy | 244.0 | 244.0 | 0.0 | 0.0 | PASS |
| category_listing_count::Home & Repair Services | 21.0 | 21.0 | 0.0 | 0.0 | PASS |
| category_listing_count::Hospitality | 275.0 | 275.0 | 0.0 | 0.0 | PASS |
| category_listing_count::Other Services | 8.0 | 8.0 | 0.0 | 0.0 | PASS |
| category_listing_count::Professional Services | 62.0 | 62.0 | 0.0 | 0.0 | PASS |
| category_listing_count::Retail | 452.0 | 452.0 | 0.0 | 0.0 | PASS |
| covered_city_category_pairs | 123.0 | 123.0 | 0.0 | 0.0 | PASS |
| city_category_universe | 144.0 | 144.0 | 0.0 | 0.0 | PASS |
| max_opportunity_score_difference | 0.01 | 0.0 | 0.01 | 0.02 | PASS |