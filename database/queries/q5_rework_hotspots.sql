-- Where does process rework occur most frequently? (activities repeated within a case)
WITH rep AS (
  SELECT case_id, case_type, activity, COALESCE(MAX(zone),'n/a') AS zone, COUNT(*) AS n FROM event_log GROUP BY case_id, case_type, activity HAVING COUNT(*) > 1),
tot AS (SELECT case_type, COUNT(DISTINCT case_id) AS cases FROM event_log GROUP BY case_type)
SELECT r.case_type, r.activity, r.zone, COUNT(*) AS rework_cases, ROUND(100.0*COUNT(*)/t.cases,2) AS pct_of_case_type
FROM rep r JOIN tot t USING(case_type) GROUP BY r.case_type, r.activity, r.zone ORDER BY rework_cases DESC;
