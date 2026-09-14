-- ============================================================================
-- KAUSHALSETU: SEED DATA (Expanded Demo Dataset)
-- 10 Workers, 21 Experiences, 19 Worker Skills, 10 Verified, 9 Knowledge Cases
-- ============================================================================

-- Standard Skills (6 canonical skills)
INSERT INTO skills (id, name, category, description) VALUES
('11111111-1111-1111-1111-111111110001', 'Board-Level Soldering', 'Electronics', 'SMD component rework, micro-soldering, BGA rework'),
('11111111-1111-1111-1111-111111110002', 'Power Supply Diagnostics', 'Electronics', 'Switched-mode power supply (SMPS) testing, capacitor replacements, rail voltage analysis'),
('11111111-1111-1111-1111-111111110003', 'Short Circuit Tracing', 'Electrical', 'Thermal camera inspection, multimeter diode mode tracing, current injection'),
('11111111-1111-1111-1111-111111110004', 'Inverter & UPS Repair', 'Power Systems', 'Pure sine wave inverter fault analysis, MOSFET replacement, battery charging circuitry'),
('11111111-1111-1111-1111-111111110005', 'Home Appliance Wiring', 'Electrical', 'Distribution board installation, MCB/ELCB tripping diagnosis, earthing testing'),
('11111111-1111-1111-1111-111111110006', 'Smart TV Panel & T-Con Repair', 'Consumer Electronics', 'T-Con board diagnostics, COF bonding, LED backlight strip replacement')
ON CONFLICT (name) DO NOTHING;

-- Demo Customer (Rahul Sharma)
INSERT INTO profiles (id, role, full_name, email, phone) VALUES
('673c60cc-51f0-4c34-b05e-75c8fd8762f6', 'customer', 'Rahul Sharma', 'customer@kaushalsetu.in', '+91 9876543210')
ON CONFLICT (id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- WORKER A — Ramesh Verma (Tier 1 - Master Board Repair Specialist)
-- ----------------------------------------------------------------------------
INSERT INTO profiles (id, role, full_name, email, phone) VALUES
('81280d57-947f-490c-825a-c2c6b8d3cc3c', 'worker', 'Ramesh Verma', 'ramesh.verma@kaushalsetu.in', '+91 9876500001')
ON CONFLICT (id) DO NOTHING;

INSERT INTO worker_profiles (
    id, user_id, professional_title, bio, years_experience, hourly_rate, service_radius_km,
    latitude, longitude, locality, city, state, postal_code, availability_status, is_verified, rating, total_reviews
) VALUES (
    '81280d57-947f-490c-825a-c2c6b8d3cc3c', '81280d57-947f-490c-825a-c2c6b8d3cc3c',
    'Senior Board Repair Specialist & Mobile Diagnostics',
    '12+ years experience in PCB board-level diagnosis, micro-soldering, and smartphone power rail troubleshooting.',
    12, 550.00, 15.00,
    19.0760, 72.8777, 'Bandra West', 'Mumbai', 'Maharashtra', '400050', 'available', true, 4.90, 48
) ON CONFLICT (user_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- WORKER B — Suresh Kumar (Tier 4 - Power Systems & Inverter Specialist)
-- ----------------------------------------------------------------------------
INSERT INTO profiles (id, role, full_name, email, phone) VALUES
('9bfe05be-8fe9-463f-862e-a3b7c44563c1', 'worker', 'Suresh Kumar', 'suresh.kumar@kaushalsetu.in', '+91 9876500002')
ON CONFLICT (id) DO NOTHING;

INSERT INTO worker_profiles (
    id, user_id, professional_title, bio, years_experience, hourly_rate, service_radius_km,
    latitude, longitude, locality, city, state, postal_code, availability_status, is_verified, rating, total_reviews
) VALUES (
    '9bfe05be-8fe9-463f-862e-a3b7c44563c1', '9bfe05be-8fe9-463f-862e-a3b7c44563c1',
    'Certified Electrical & Inverter Specialist',
    'ITI certified electrician specializing in household wiring, inverter PCB power overload, and motor rewinding.',
    8, 400.00, 12.00,
    19.0800, 72.8800, 'Kurla', 'Mumbai', 'Maharashtra', '400070', 'available', true, 4.75, 31
) ON CONFLICT (user_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- WORKER C — Vikram Singh (Tier 5 - General Electrician)
-- ----------------------------------------------------------------------------
INSERT INTO profiles (id, role, full_name, email, phone) VALUES
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb03', 'worker', 'Vikram Singh', 'vikram.singh@kaushalsetu.in', '+91 9876500003')
ON CONFLICT (id) DO NOTHING;

INSERT INTO worker_profiles (
    id, user_id, professional_title, bio, years_experience, hourly_rate, service_radius_km,
    latitude, longitude, locality, city, state, postal_code, availability_status, is_verified, rating, total_reviews
) VALUES (
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb03', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb03',
    'General House Electrician & Wiring Technician',
    'Specialized in residential wiring installation, switchboard repair, MCB replacement, and house earthing.',
    6, 350.00, 10.00,
    19.0400, 72.8500, 'Dharavi', 'Mumbai', 'Maharashtra', '400017', 'available', false, 4.50, 18
) ON CONFLICT (user_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- WORKER D — Amit Shah (Tier 2 - Smartphone Repair Specialist)
-- ----------------------------------------------------------------------------
INSERT INTO profiles (id, role, full_name, email, phone) VALUES
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb04', 'worker', 'Amit Shah', 'amit.shah@kaushalsetu.in', '+91 9876500004')
ON CONFLICT (id) DO NOTHING;

INSERT INTO worker_profiles (
    id, user_id, professional_title, bio, years_experience, hourly_rate, service_radius_km,
    latitude, longitude, locality, city, state, postal_code, availability_status, is_verified, rating, total_reviews
) VALUES (
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb04', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb04',
    'Smartphone Motherboard & Power Fault Specialist',
    'Expert in Samsung & Android device troubleshooting, board-level power diagnostics, and drop damage repairs.',
    9, 500.00, 14.00,
    19.1190, 72.8470, 'Andheri West', 'Mumbai', 'Maharashtra', '400058', 'available', true, 4.85, 39
) ON CONFLICT (user_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- WORKER E — Neha Patel (Tier 2 - Electronics / PCB Repair Specialist)
-- ----------------------------------------------------------------------------
INSERT INTO profiles (id, role, full_name, email, phone) VALUES
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb05', 'worker', 'Neha Patel', 'neha.patel@kaushalsetu.in', '+91 9876500005')
ON CONFLICT (id) DO NOTHING;

INSERT INTO worker_profiles (
    id, user_id, professional_title, bio, years_experience, hourly_rate, service_radius_km,
    latitude, longitude, locality, city, state, postal_code, availability_status, is_verified, rating, total_reviews
) VALUES (
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb05', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb05',
    'PCB Power Circuit & Micro-Electronics Engineer',
    'Specialized in micro-soldering, short circuit tracing, and electronic board power fault rectification.',
    7, 480.00, 12.00,
    19.1170, 72.9050, 'Powai', 'Mumbai', 'Maharashtra', '400076', 'available', true, 4.80, 27
) ON CONFLICT (user_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- WORKER F — Arjun Rao (Tier 3 - Mobile Display & Charging Technician)
-- ----------------------------------------------------------------------------
INSERT INTO profiles (id, role, full_name, email, phone) VALUES
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb06', 'worker', 'Arjun Rao', 'arjun.rao@kaushalsetu.in', '+91 9876500006')
ON CONFLICT (id) DO NOTHING;

INSERT INTO worker_profiles (
    id, user_id, professional_title, bio, years_experience, hourly_rate, service_radius_km,
    latitude, longitude, locality, city, state, postal_code, availability_status, is_verified, rating, total_reviews
) VALUES (
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb06', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb06',
    'Mobile Display & Charging Port Repair Technician',
    'Focused on smartphone screen replacements, USB-C charging IC replacements, and battery servicing.',
    5, 380.00, 10.00,
    19.0180, 72.8430, 'Dadar', 'Mumbai', 'Maharashtra', '400028', 'available', false, 4.60, 22
) ON CONFLICT (user_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- WORKER G — Priya Nair (Tier 3 - TV & Consumer Electronics Specialist)
-- ----------------------------------------------------------------------------
INSERT INTO profiles (id, role, full_name, email, phone) VALUES
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb07', 'worker', 'Priya Nair', 'priya.nair@kaushalsetu.in', '+91 9876500007')
ON CONFLICT (id) DO NOTHING;

INSERT INTO worker_profiles (
    id, user_id, professional_title, bio, years_experience, hourly_rate, service_radius_km,
    latitude, longitude, locality, city, state, postal_code, availability_status, is_verified, rating, total_reviews
) VALUES (
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb07', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb07',
    'Smart TV & Consumer Electronics Board Specialist',
    'Expert in Samsung Smart TV power boards, T-Con panels, and home media electronics troubleshooting.',
    8, 450.00, 15.00,
    19.2180, 72.9780, 'Thane West', 'Mumbai', 'Maharashtra', '400601', 'available', true, 4.75, 33
) ON CONFLICT (user_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- WORKER H — Mehul Chhabra (Tier 4 - Inverter & UPS Power Systems)
-- ----------------------------------------------------------------------------
INSERT INTO profiles (id, role, full_name, email, phone) VALUES
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb08', 'worker', 'Mehul Chhabra', 'mehul.chhabra@kaushalsetu.in', '+91 9876500008')
ON CONFLICT (id) DO NOTHING;

INSERT INTO worker_profiles (
    id, user_id, professional_title, bio, years_experience, hourly_rate, service_radius_km,
    latitude, longitude, locality, city, state, postal_code, availability_status, is_verified, rating, total_reviews
) VALUES (
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb08', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb08',
    'Industrial Inverter & Heavy UPS Systems Engineer',
    'Specialized in high-voltage power backups, commercial inverters, battery bank maintenance, and overload circuits.',
    10, 520.00, 18.00,
    19.0330, 73.0290, 'Vashi', 'Navi Mumbai', 'Maharashtra', '400703', 'available', true, 4.88, 41
) ON CONFLICT (user_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- WORKER I — Karan Joshi (Tier 5 - Electrical Diagnostics & Tracing)
-- ----------------------------------------------------------------------------
INSERT INTO profiles (id, role, full_name, email, phone) VALUES
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb09', 'worker', 'Karan Joshi', 'karan.joshi@kaushalsetu.in', '+91 9876500009')
ON CONFLICT (id) DO NOTHING;

INSERT INTO worker_profiles (
    id, user_id, professional_title, bio, years_experience, hourly_rate, service_radius_km,
    latitude, longitude, locality, city, state, postal_code, availability_status, is_verified, rating, total_reviews
) VALUES (
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb09', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb09',
    'Household Electrical Fault & Short Circuit Specialist',
    'Expert in home electrical wiring short circuit detection, MCB/ELCB tripping, and phase imbalance troubleshooting.',
    7, 420.00, 12.00,
    19.2300, 72.8560, 'Borivali West', 'Mumbai', 'Maharashtra', '400092', 'available', true, 4.70, 29
) ON CONFLICT (user_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- WORKER J — Sneha Kulkarni (Tier 5 - Home Electrical Wiring)
-- ----------------------------------------------------------------------------
INSERT INTO profiles (id, role, full_name, email, phone) VALUES
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb10', 'worker', 'Sneha Kulkarni', 'sneha.kulkarni@kaushalsetu.in', '+91 9876500010')
ON CONFLICT (id) DO NOTHING;

INSERT INTO worker_profiles (
    id, user_id, professional_title, bio, years_experience, hourly_rate, service_radius_km,
    latitude, longitude, locality, city, state, postal_code, availability_status, is_verified, rating, total_reviews
) VALUES (
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb10', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb10',
    'Residential Wiring & Switchboard Repair Technician',
    'Certified electrician focusing on residential switchboard installations, light fixtures, and basic appliance wiring.',
    4, 320.00, 10.00,
    19.0620, 72.8970, 'Chembur', 'Mumbai', 'Maharashtra', '400071', 'available', false, 4.55, 15
) ON CONFLICT (user_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- Worker Skills Link (19 Skill Relationships)
-- ----------------------------------------------------------------------------
INSERT INTO worker_skills (worker_id, skill_id, proficiency_level, years_experience, is_primary) VALUES
('81280d57-947f-490c-825a-c2c6b8d3cc3c', '11111111-1111-1111-1111-111111110001', 'expert', 12, true),
('81280d57-947f-490c-825a-c2c6b8d3cc3c', '11111111-1111-1111-1111-111111110002', 'expert', 10, false),
('81280d57-947f-490c-825a-c2c6b8d3cc3c', '11111111-1111-1111-1111-111111110003', 'expert', 12, false),
('9bfe05be-8fe9-463f-862e-a3b7c44563c1', '11111111-1111-1111-1111-111111110004', 'expert', 8, true),
('9bfe05be-8fe9-463f-862e-a3b7c44563c1', '11111111-1111-1111-1111-111111110005', 'advanced', 8, false),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb03', '11111111-1111-1111-1111-111111110005', 'intermediate', 6, true),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb04', '11111111-1111-1111-1111-111111110001', 'expert', 9, true),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb04', '11111111-1111-1111-1111-111111110002', 'advanced', 7, false),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb05', '11111111-1111-1111-1111-111111110001', 'advanced', 7, true),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb05', '11111111-1111-1111-1111-111111110003', 'expert', 7, false),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb06', '11111111-1111-1111-1111-111111110002', 'intermediate', 5, true),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb07', '11111111-1111-1111-1111-111111110002', 'advanced', 8, false),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb07', '11111111-1111-1111-1111-111111110006', 'expert', 8, true),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb08', '11111111-1111-1111-1111-111111110004', 'expert', 10, true),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb09', '11111111-1111-1111-1111-111111110003', 'advanced', 7, true),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb09', '11111111-1111-1111-1111-111111110005', 'advanced', 7, false),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb10', '11111111-1111-1111-1111-111111110005', 'intermediate', 4, true)
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------------------
-- Certificates
-- ----------------------------------------------------------------------------
INSERT INTO certificates (id, worker_id, certificate_name, issuing_organization, issue_date, verification_status) VALUES
('f1111111-1111-1111-1111-111111110001', '81280d57-947f-490c-825a-c2c6b8d3cc3c', 'Advanced Micro-Soldering Certification (IPC-7711/7721)', 'National Electronics Association', '2021-06-15', 'verified'),
('f1111111-1111-1111-1111-111111110002', '9bfe05be-8fe9-463f-862e-a3b7c44563c1', 'National Trade Certificate (NTC) Electrician', 'National Council for Vocational Training', '2018-08-20', 'verified')
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------------------
-- Experiences (21 Total Experiences across 10 Workers)
-- ----------------------------------------------------------------------------
INSERT INTO experiences (
    id, worker_id, title, problem_description, diagnosis, outcome_summary,
    repair_type, device_category, brand, model, difficulty, verification_status, experience_status, verification_confidence
) VALUES
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee01', '81280d57-947f-490c-825a-c2c6b8d3cc3c',
    'Samsung Galaxy S23 Power Rail Short Circuit Repair',
    'Samsung Galaxy S23 fell down and now does not turn on. Device completely dead drawing 0mA; short on VDD_MAIN rail traced to damaged PMIC decoupling capacitor after drop.',
    'Dead phone drawing 0mA after drop; short on VDD_MAIN rail traced to damaged PMIC decoupling capacitor.',
    'Replaced PMIC C4021 decoupling capacitor and restored full power boot.',
    'board-level component replacement', 'Smartphone / Electronics', 'Samsung', 'Galaxy S23', 'advanced', 'verified', 'verified', 0.95
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee02', '81280d57-947f-490c-825a-c2c6b8d3cc3c',
    'Samsung Galaxy S22 Ultra No Booting Post Impact',
    'Galaxy S22 Ultra dropped on hard surface. Screen black, motherboard short circuit detected.',
    'Sub-PMIC short circuit due to hairline solder crack under power IC.',
    'Reballing Sub-PMIC IC chip restored device functionality and fast charging.',
    'micro-soldering & BGA reballing', 'Smartphone / Electronics', 'Samsung', 'Galaxy S22 Ultra', 'advanced', 'verified', 'verified', 0.92
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee03', '81280d57-947f-490c-825a-c2c6b8d3cc3c',
    'OnePlus 11 5G Dead Motherboard Recovery',
    'OnePlus 11 shut down suddenly after water splash, short circuit on charging line.',
    'Corroded diode and shorted input capacitor on charging controller circuit.',
    'Cleaned corrosion, replaced Schottky diode and capacitor.',
    'SMD component rework', 'Smartphone / Electronics', 'OnePlus', '11 5G', 'intermediate', 'unverified', 'submitted', 0.00
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee04', '9bfe05be-8fe9-463f-862e-a3b7c44563c1',
    'Luminous 1100VA Inverter Continuous Overload Repair',
    'Inverter beeps continuously indicating overload even with zero connected load on backup.',
    'Damaged MOSFET pair on the primary H-bridge stage causing feedback loop sensing anomaly.',
    'Replaced IRF3205 MOSFETs and gate driver resistors; load test passed.',
    'power electronics PCB repair', 'Power Systems', 'Luminous', 'Zelio 1100', 'intermediate', 'verified', 'verified', 0.88
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee05', '9bfe05be-8fe9-463f-862e-a3b7c44563c1',
    'Microtek UPS Battery Charging Board Repair',
    'UPS failing to charge battery during mains power availability.',
    'Blown rectifier diode and failed relay on charging control section.',
    'Replaced 12V relay and power diode.',
    'component replacement', 'Power Systems', 'Microtek', 'Heritage 1000', 'intermediate', 'unverified', 'submitted', 0.00
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee06', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb03',
    'Residential Apartment Main Distribution Board Rewiring',
    'Frequent power tripping across kitchen power points under high load.',
    'Loose neutral connection and overloaded 16A single-pole MCB.',
    'Upgraded MCB to 25A C-curve and rebalanced load across 3 phases.',
    'household electrical wiring', 'Home Electrical', 'Havells', 'DB-12Way', 'intermediate', 'unverified', 'submitted', 0.00
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee07', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb03',
    'Modular Switchboard Installation and Earthing Fix',
    'Light shocks felt on metallic casing of water heater switchboard.',
    'Improper earthing resistance (>15 ohms) and corroded earthing wire connection.',
    'Replaced copper earthing wire and installed modular 6-gang switchboard.',
    'switchboard installation', 'Home Electrical', 'Anchor', 'Roma Classic', 'basic', 'unverified', 'submitted', 0.00
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee08', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb04',
    'Samsung Galaxy S22 No Power After Hard Drop',
    'Samsung Galaxy S22 dropped down and became completely dead with no screen response.',
    'Main power rail capacitor shorted due to physical impact near PM8350 IC.',
    'Removed shorted SMD capacitor and replaced PMIC power rail line.',
    'smartphone board repair', 'Smartphone / Electronics', 'Samsung', 'Galaxy S22', 'advanced', 'verified', 'verified', 0.94
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee09', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb04',
    'Samsung Galaxy A54 Charging Failure & Boot Loop',
    'Galaxy A54 stuck on charging logo and refusing to power on completely.',
    'Damaged USB charging controller IC (OVP IC tripped).',
    'Replaced OVP IC and restored normal battery charging curve.',
    'board-level IC replacement', 'Smartphone / Electronics', 'Samsung', 'Galaxy A54', 'intermediate', 'verified', 'verified', 0.90
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee10', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb05',
    'Smartphone Board-Level Power Fault & Short Rectification',
    'Android mobile device drawing excessive standby current, getting hot near CPU.',
    'Short circuit on secondary power line VBAT_SENSE caused by cracked decoupling cap.',
    'Thermal imaging located shorted cap; replaced and restored normal current draw.',
    'short circuit tracing & cap replacement', 'Smartphone / Electronics', 'Xiaomi', 'Redmi Note 12', 'advanced', 'verified', 'verified', 0.91
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee11', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb05',
    'Damaged PCB Power Circuit Component Rework',
    'Tablet motherboard dead after non-genuine charger connected.',
    'Burnt charging MOSFET and blown input fuse diode.',
    'Replaced protection diode and power MOSFET with SMD rework station.',
    'PCB power circuit rework', 'Electronics / PCB', 'Lenovo', 'Tab M10', 'intermediate', 'unverified', 'submitted', 0.00
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee12', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb06',
    'Samsung Galaxy S21 Ultra Cracked Display Replacement',
    'Samsung Galaxy S21 screen shattered after drop, touchscreen unresponsive.',
    'FHD AMOLED panel glass fracture and digitizer ribbon tear.',
    'Installed original Samsung display assembly and recalibrated fingerprint sensor.',
    'display assembly replacement', 'Smartphone / Electronics', 'Samsung', 'Galaxy S21 Ultra', 'intermediate', 'verified', 'verified', 0.89
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee13', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb06',
    'Smartphone USB-C Charging Port Replacement',
    'Phone charges intermittently only when cable is held at specific angle.',
    'Worn pin contacts and damaged flex cable connector inside Type-C port.',
    'Soldered new sub-board charging port connector.',
    'charging port replacement', 'Smartphone / Electronics', 'Vivo', 'V25 Pro', 'basic', 'unverified', 'submitted', 0.00
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee14', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb07',
    'Samsung 55-inch Smart TV Power Supply Board Repair',
    'Samsung 4K TV standby LED blinking, screen fails to power on.',
    'Blown electrolytic capacitors in SMPS secondary power section.',
    'Replaced low-ESR capacitors on SMPS board; TV powered up normally.',
    'TV power supply repair', 'Consumer Electronics / TV', 'Samsung', 'UA55TU8000', 'intermediate', 'verified', 'verified', 0.93
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee15', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb07',
    'LG LED TV T-Con Board Distortion Fixing',
    'Vertical colored lines appeared across LED TV screen.',
    'T-Con board timing IC overheating and loose ribbon connector.',
    'Cleaned ribbon contacts and applied thermal paste to T-Con IC.',
    'T-Con board diagnostics', 'Consumer Electronics / TV', 'LG', '43UQ7550', 'intermediate', 'unverified', 'submitted', 0.00
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee16', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb08',
    'Commercial 3KVA UPS Power Failure Diagnosis',
    '3KVA Online UPS shutting down instantly upon mains outage.',
    'Degraded lead-acid battery bank cell short circuit and relay failure.',
    'Replaced 4x 12V batteries and recalibrated float charging voltage.',
    'UPS power system overhaul', 'Power Systems', 'APC', 'Smart-UPS 3000', 'advanced', 'verified', 'verified', 0.90
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee17', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb08',
    'Exide Inverter Overload Fault & Thermal Trip Fix',
    'Inverter tripping on thermal protection after 10 minutes of usage.',
    'Clogged heat-sink cooling fan and dried thermal grease on MOSFET bridge.',
    'Replaced 12V DC cooling fan and reapplied thermal compound.',
    'inverter thermal system repair', 'Power Systems', 'Exide', 'GXT 1050', 'intermediate', 'unverified', 'submitted', 0.00
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee18', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb09',
    'Household Main MCB Tripping & Short Circuit Tracing',
    'Main 32A MCB trips repeatedly every time bedroom air conditioner turns on.',
    'Insulation breakdown in AC concealed copper wiring causing line-to-earth short.',
    'Traced short circuit location with insulation tester and replaced damaged wire section.',
    'short circuit tracing', 'Home Electrical', 'Schneider', 'Acti9 MCB', 'intermediate', 'verified', 'verified', 0.88
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee19', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb09',
    '3-Phase Distribution Board Neutral Wire Burn Fix',
    'Unstable voltage fluctuating between 180V and 290V across home appliances.',
    'Loose neutral busbar screw causing floating neutral condition.',
    'Re-terminated main neutral connector and installed voltage protection relay.',
    'electrical distribution board repair', 'Home Electrical', 'Legrand', 'DLP DB', 'advanced', 'unverified', 'submitted', 0.00
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee20', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb10',
    'Kitchen Appliance Switchboard Repair & Socket Replacement',
    '16A microwave power socket sparking and smelling burnt.',
    'Melted terminal screws due to loose high-draw connection.',
    'Replaced heavy-duty 16A socket and switch unit with flame-retardant box.',
    'switchboard repair', 'Home Electrical', 'Crabtree', 'Athena', 'basic', 'unverified', 'submitted', 0.00
),
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee21', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb10',
    'Ceiling Fan Regulator & Wiring Connection',
    'Ceiling fan running at full speed only, regulator knob ineffective.',
    'Blown capacitor inside step-type regulator module.',
    'Installed new hum-free electronic fan regulator.',
    'appliance wiring repair', 'Home Electrical', 'Orient', 'Reg-5S', 'basic', 'unverified', 'submitted', 0.00
)
ON CONFLICT (id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- Knowledge Cases (9 Realistic Cases)
-- ----------------------------------------------------------------------------
INSERT INTO knowledge_cases (
    id, worker_id, experience_id, title, problem_summary, diagnosis_summary, solution_summary,
    lesson_learned, difficulty_level, device_category, brand, model, visibility_status, is_verified
) VALUES
(
    'dddddddd-dddd-dddd-dddd-dddddddddd01', '81280d57-947f-490c-825a-c2c6b8d3cc3c', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee01',
    'Samsung S23 No Power After Physical Drop',
    'Device completely dead following a drop, drawing 0mA on DC power supply.',
    'Primary power management IC (PMIC) cracked under shielding bracket, VBAT rail shorted to ground.',
    'Carefully lifted the shield with hot air at 320C, replaced damaged PMIC and decoupling capacitor C4021.',
    'Always inspect the inductor pads next to PMIC for trace hairline fractures after drop impact.',
    'advanced', 'Smartphone / PCB', 'Samsung', 'Galaxy S23', 'published', true
),
(
    'dddddddd-dddd-dddd-dddd-dddddddddd02', '9bfe05be-8fe9-463f-862e-a3b7c44563c1', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee04',
    'Luminous 1100VA Inverter Continuous Overload Alarm',
    'Inverter beeps continuously indicating overload even with zero connected load on backup.',
    'Damaged MOSFET pair on the primary H-bridge stage causing feedback loop sensing anomaly.',
    'Replaced IRF3205 MOSFETs and 10 ohm gate resistors. Tested inverter under 600W resistive load.',
    'Always replace gate driver resistors in pairs whenever MOSFETs fail in an inverter circuit.',
    'intermediate', 'Power Inverter', 'Luminous', 'Zelio 1100', 'published', true
),
(
    'dddddddd-dddd-dddd-dddd-dddddddddd03', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb04', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee08',
    'Samsung S22 No Power After Drop Diagnosis',
    'Galaxy S22 phone dead after fall, no boot vibration or current draw.',
    'Impact caused Ceramic Capacitor on PM8350 rail to short internally.',
    'Injected 1.8V to isolate heating cap using thermal camera, replaced cap.',
    'Current injection at low voltage safely isolates shorted caps on modern 4nm phone logic boards.',
    'advanced', 'Smartphone / PCB', 'Samsung', 'Galaxy S22', 'published', true
),
(
    'dddddddd-dddd-dddd-dddd-dddddddddd04', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb05', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee10',
    'Smartphone Board-Level Power Diagnosis & Thermal Tracing',
    'Mobile motherboard drawing high standby current and heating up.',
    'Secondary rail short circuit traced via micro-multimeter diode mode testing.',
    'Removed shorted component and verified voltage rail stability.',
    'Diode mode values comparing ground reference are faster than resistance readings for SMD shorts.',
    'advanced', 'Smartphone / Electronics', 'Xiaomi', 'Redmi Note 12', 'published', true
),
(
    'dddddddd-dddd-dddd-dddd-dddddddddd05', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb07', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee14',
    'Samsung TV Power Supply Board Failure Repair',
    'Samsung Smart TV red LED blinks 2 times, no backlight or audio.',
    'Blown filter capacitors in SMPS secondary stage causing voltage dip.',
    'Replaced blown 105C high-temp electrolytic capacitors on power board.',
    'Check secondary rail voltages under standby before replacing whole TV power board.',
    'intermediate', 'Consumer Electronics / TV', 'Samsung', 'UA55TU8000', 'published', true
),
(
    'dddddddd-dddd-dddd-dddd-dddddddddd06', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb09', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee18',
    'Household MCB Tripping & Short Circuit Isolation',
    'Main circuit breaker trips constantly when heavy load turned on.',
    'Wiring insulation degradation creating phase-to-earth leakage.',
    'Isolated damaged wiring segment using megohmmeter continuity tester.',
    'Always test line-to-earth resistance across individual circuits when main RCD/MCB trips.',
    'intermediate', 'Home Electrical', 'Schneider', 'Acti9 MCB', 'published', true
),
(
    'dddddddd-dddd-dddd-dddd-dddddddddd07', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb08', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee16',
    '3KVA Online UPS Battery Bank Failover Troubleshooting',
    'Commercial UPS fails to support load during blackouts.',
    'High internal resistance in one degraded battery dragging down entire DC bus.',
    'Replaced weak battery cell and equalized charge voltages across string.',
    'Measure individual battery voltage under load, not open-circuit voltage.',
    'advanced', 'Power Systems', 'APC', 'Smart-UPS 3000', 'published', true
),
(
    'dddddddd-dddd-dddd-dddd-dddddddddd08', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb06', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee12',
    'Samsung Galaxy S-Series Curved Display Replacement',
    'Curved AMOLED screen glass smashed after fall.',
    'Digitizer glass broken; OLED panel functional but fragile flex cable pinched.',
    'Extracted frame assembly with isopropyl alcohol and glued original panel.',
    'Heat frame to 80C before lifting curved glass edges to prevent OLED panel tearing.',
    'intermediate', 'Smartphone / Electronics', 'Samsung', 'Galaxy S21 Ultra', 'published', true
),
(
    'dddddddd-dddd-dddd-dddd-dddddddddd09', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb03', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee06',
    'Distribution Board Phase Balancing for Residential Apartments',
    'Uneven voltage causing lights to dim when air conditioner starts.',
    'Single phase heavily overloaded while other 2 phases underutilized.',
    'Redistributed high-amperage appliances evenly across 3 incoming phases.',
    'Calculate peak concurrent wattage for kitchen and AC points during DB wiring layout.',
    'intermediate', 'Home Electrical', 'Havells', 'DB-12Way', 'published', false
)
ON CONFLICT (id) DO NOTHING;
