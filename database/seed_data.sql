-- BusinessPulse deterministic lookup seed values.
-- These rows make the dimensions and the opportunity methodology available
-- before the first listing import. The importer upserts on names as well.

INSERT IGNORE INTO dim_city
    (city_id, city_name, state_name, country, latitude, longitude)
VALUES
    (1,  'Pune',       'Maharashtra',    'India', 18.5213738, 73.8545071),
    (2,  'Mumbai',     'Maharashtra',    'India', 19.0549990, 72.8692035),
    (3,  'Bengaluru',  'Karnataka',      'India', 12.9880551, 77.6219718),
    (4,  'Delhi',      'Delhi',          'India', 28.6440375, 77.0920865),
    (5,  'Hyderabad',  'Telangana',      'India', 17.4262349, 78.4305490),
    (6,  'Chennai',    'Tamil Nadu',     'India', 13.0435676, 80.2334108),
    (7,  'Kolkata',    'West Bengal',    'India', 22.5330500, 88.3505489),
    (8,  'Ahmedabad',  'Gujarat',        'India', 23.0215374, 72.5800568),
    (9,  'Jaipur',     'Rajasthan',      'India', 26.9154576, 75.8189817),
    (10, 'Surat',      'Gujarat',        'India', 21.2094892, 72.8317058),
    (11, 'Lucknow',    'Uttar Pradesh',  'India', 26.8381000, 80.9346001),
    (12, 'Chandigarh', 'Chandigarh',     'India', 30.7334421, 76.7797143);

INSERT IGNORE INTO dim_category
    (category_id, category_name, display_order, description)
VALUES
    (1,  'Food & Beverage',       1,  'Restaurants, cafes, bars, bakeries and food shops'),
    (2,  'Retail',                2,  'General merchandise and specialty shops'),
    (3,  'Health & Pharmacy',     3,  'Pharmacies, clinics, hospitals and health shops'),
    (4,  'Finance & Banking',     4,  'Banks, exchange services and financial offices'),
    (5,  'Professional Services', 5,  'Legal, accounting, real estate and business services'),
    (6,  'Hospitality',           6,  'Hotels, guest houses and hostels'),
    (7,  'Beauty & Personal Care',7,  'Beauty salons, hairdressers and personal-care shops'),
    (8,  'Automotive',            8,  'Vehicle sales, repair, parts and fuel'),
    (9,  'Education & Training',  9,  'Driving, language, music and training providers'),
    (10, 'Fitness & Recreation',  10, 'Gyms, sports venues and entertainment'),
    (11, 'Home & Repair Services',11, 'Hardware, building materials and trades'),
    (12, 'Other Services',        12, 'Laundry, tailoring, pet care and other services');

INSERT IGNORE INTO dim_source
    (source_id, source_name, source_type, source_url, license_name, license_url, attribution)
VALUES
    (1,
     'OpenStreetMap (Overpass API)',
     'Open Data - Crowdsourced Map',
     'https://overpass-api.de/',
     'Open Database License (ODbL) 1.0',
     'https://opendatacommons.org/licenses/odbl/1-0/',
     '© OpenStreetMap contributors');

INSERT INTO opportunity_config
    (config_id, underrepresentation_weight, city_breadth_weight, reliability_weight,
     high_threshold, medium_threshold, min_city_listings, min_category_national_count)
VALUES
    (1, 0.6000, 0.2500, 0.1500, 60.00, 40.00, 20, 5)
ON DUPLICATE KEY UPDATE
    underrepresentation_weight = 0.6000,
    city_breadth_weight = 0.2500,
    reliability_weight = 0.1500,
    high_threshold = 60.00,
    medium_threshold = 40.00,
    min_city_listings = 20,
    min_category_national_count = 5;
