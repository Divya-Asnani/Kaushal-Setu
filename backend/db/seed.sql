-- ============================================================================
-- KAUSHALSETU: SEED DATA
-- Electrical & Technician repair skills, profiles, and knowledge base
-- ============================================================================

-- Standard Skills
INSERT INTO skills (id, name, category, description) VALUES
('11111111-1111-1111-1111-111111110001', 'Board-Level Soldering', 'Electronics', 'SMD component rework, micro-soldering, BGA rework'),
('11111111-1111-1111-1111-111111110002', 'Power Supply Diagnostics', 'Electronics', 'Switched-mode power supply (SMPS) testing, capacitor replacements, rail voltage analysis'),
('11111111-1111-1111-1111-111111110003', 'Short Circuit Tracing', 'Electrical', 'Thermal camera inspection, multimeter diode mode tracing, current injection'),
('11111111-1111-1111-1111-111111110004', 'Inverter & UPS Repair', 'Power Systems', 'Pure sine wave inverter fault analysis, MOSFET replacement, battery charging circuitry'),
('11111111-1111-1111-1111-111111110005', 'Home Appliance Wiring', 'Electrical', 'Distribution board installation, MCB/ELCB tripping diagnosis, earthing testing'),
('11111111-1111-1111-1111-111111110006', 'Smart TV Panel & T-Con Repair', 'Consumer Electronics', 'T-Con board diagnostics, COF bonding, LED backlight strip replacement')
ON CONFLICT (name) DO NOTHING;

-- Demo Profiles (UUIDs match Supabase Auth identities)
-- 1. Demo Customer (Rahul Sharma)
INSERT INTO profiles (id, role, full_name, email, phone) VALUES
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'customer', 'Rahul Sharma', 'customer@kaushalsetu.in', '+91 9876543210')
ON CONFLICT (id) DO NOTHING;

-- 2. Demo Worker 1 (Ramesh Verma - Master Board Technician)
INSERT INTO profiles (id, role, full_name, email, phone) VALUES
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb01', 'worker', 'Ramesh Verma', 'ramesh.verma@kaushalsetu.in', '+91 9876500001')
ON CONFLICT (id) DO NOTHING;

INSERT INTO worker_profiles (
    id, user_id, headline, bio, experience_years, hourly_rate, service_radius_km,
    latitude, longitude, locality, city, state, is_available, is_verified, rating, total_reviews
) VALUES (
    'cccccccc-cccc-cccc-cccc-cccccccccc01',
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb01',
    'Senior Board Repair Specialist & Electrician',
    '12+ years experience in PCB board-level diagnosis, micro-soldering, and home inverter circuitry.',
    12, 550.00, 15.00,
    19.0760, 72.8777, 'Bandra West', 'Mumbai', 'Maharashtra', true, true, 4.90, 48
) ON CONFLICT (user_id) DO NOTHING;

-- 3. Demo Worker 2 (Suresh Kumar - Power Systems & Appliances)
INSERT INTO profiles (id, role, full_name, email, phone) VALUES
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb02', 'worker', 'Suresh Kumar', 'suresh.kumar@kaushalsetu.in', '+91 9876500002')
ON CONFLICT (id) DO NOTHING;

INSERT INTO worker_profiles (
    id, user_id, headline, bio, experience_years, hourly_rate, service_radius_km,
    latitude, longitude, locality, city, state, is_available, is_verified, rating, total_reviews
) VALUES (
    'cccccccc-cccc-cccc-cccc-cccccccccc02',
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb02',
    'Certified Electrical & Inverter Specialist',
    'ITI certified electrician specializing in household wiring, tripping faults, and motor rewinding.',
    8, 400.00, 12.00,
    19.0800, 72.8800, 'Kurla', 'Mumbai', 'Maharashtra', true, true, 4.75, 31
) ON CONFLICT (user_id) DO NOTHING;

-- Worker Skills Link
INSERT INTO worker_skills (worker_id, skill_id, proficiency_level, verified) VALUES
('cccccccc-cccc-cccc-cccc-cccccccccc01', '11111111-1111-1111-1111-111111110001', 'expert', true),
('cccccccc-cccc-cccc-cccc-cccccccccc01', '11111111-1111-1111-1111-111111110002', 'expert', true),
('cccccccc-cccc-cccc-cccc-cccccccccc01', '11111111-1111-1111-1111-111111110003', 'expert', true),
('cccccccc-cccc-cccc-cccc-cccccccccc02', '11111111-1111-1111-1111-111111110004', 'expert', true),
('cccccccc-cccc-cccc-cccc-cccccccccc02', '11111111-1111-1111-1111-111111110005', 'advanced', true)
ON CONFLICT DO NOTHING;

-- Worker Certificates
INSERT INTO certificates (worker_id, title, issuing_organization, issue_date, is_verified) VALUES
('cccccccc-cccc-cccc-cccc-cccccccccc01', 'Advanced Micro-Soldering Certification (IPC-7711/7721)', 'National Electronics Association', '2021-06-15', true),
('cccccccc-cccc-cccc-cccc-cccccccccc02', 'National Trade Certificate (NTC) Electrician', 'National Council for Vocational Training', '2018-08-20', true)
ON CONFLICT DO NOTHING;

-- Knowledge Hub Seed Cases
INSERT INTO knowledge_cases (
    id, worker_id, title, problem_summary, diagnosis, solution, lesson_learned, difficulty, device_category, brand, model, is_published, is_verified
) VALUES
(
    'dddddddd-dddd-dddd-dddd-dddddddddd01',
    'cccccccc-cccc-cccc-cccc-cccccccccc01',
    'Samsung S23 No Power After Physical Drop',
    'Device completely dead following a drop, drawing 0mA on DC power supply.',
    'Primary power management IC (PMIC) cracked under shielding bracket, VBAT rail shorted to ground.',
    'Carefully lifted the shield with hot air at 320C, replaced damaged PMIC and decoupling capacitor C4021.',
    'Always inspect the inductor pads next to PMIC for trace hairline fractures after drop impact.',
    'advanced', 'Smartphone / PCB', 'Samsung', 'Galaxy S23', true, true
),
(
    'dddddddd-dddd-dddd-dddd-dddddddddd02',
    'cccccccc-cccc-cccc-cccc-cccccccccc02',
    'Luminous 1100VA Inverter Continuous Overload Alarm',
    'Inverter beeps continuously indicating overload even with zero connected load on backup.',
    'Damaged MOSFET pair on the primary H-bridge stage causing feedback loop sensing anomaly.',
    'Replaced IRF3205 MOSFETs and 10 ohm gate resistors. Tested inverter under 600W resistive load.',
    'Always replace gate driver resistors in pairs whenever MOSFETs fail in an inverter circuit.',
    'intermediate', 'Power Inverter', 'Luminous', 'Zelio 1100', true, true
)
ON CONFLICT DO NOTHING;
