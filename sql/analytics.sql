-- Monthly A&E activity and quarterly KH03 beds are separate NHS England
-- publications with different reporting populations. Do not join their rows.
DROP VIEW IF EXISTS monthly_pressure;
CREATE VIEW monthly_pressure AS
SELECT month, total_attendances, type1_attendances, type2_attendances,
       type3_attendances, type1_admissions, type2_admissions, type3_admissions,
       ae_admissions, other_emergency_admissions,
       total_emergency_admissions, dta_wait_over_4h, dta_wait_over_12h
FROM national_monthly;

DROP VIEW IF EXISTS quarterly_beds;
CREATE VIEW quarterly_beds AS
SELECT quarter_end, available_beds, occupied_beds, occupancy_pct,
       reporting_organisations
FROM national_beds_quarterly;
