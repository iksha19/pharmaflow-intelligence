-- Which data-quality issues require remediation first? Materials with defects ranked by downstream rework/skipped-verification impact.
WITH x AS (
  SELECT m.material_id, m.category,
    (m.uom IS NULL)+(m.shelf_life_days IS NULL)+(m.storage_condition IS NULL)+(m.abc_class IS NULL)+(m.gmp_relevant IS NULL)+(m.net_weight_kg IS NULL)
      + (m.uom NOT IN ('EA','KG','G','L','ML','BOX')) AS defects,
    (m.storage_condition IS NULL) AS no_storage_cond, (m.uom NOT IN ('EA','KG','G','L','ML','BOX')) AS bad_uom FROM materials m),
d AS (SELECT l.material_id, COUNT(*) AS deliveries, SUM(i.rework_flag) AS rework_deliveries, SUM(i.verification_ts IS NULL) AS skipped_verification
      FROM inbound_deliveries i JOIN po_lines l USING(po_line_id) GROUP BY l.material_id)
SELECT x.material_id, x.category, x.defects, x.no_storage_cond, x.bad_uom, COALESCE(d.deliveries,0) AS deliveries,
       COALESCE(d.rework_deliveries,0) AS rework_deliveries, COALESCE(d.skipped_verification,0) AS skipped_verification,
       COALESCE(d.rework_deliveries,0)+COALESCE(d.skipped_verification,0) AS impact_events,
       RANK() OVER (ORDER BY COALESCE(d.rework_deliveries,0)+COALESCE(d.skipped_verification,0) DESC) AS priority_rank
FROM x LEFT JOIN d USING(material_id) WHERE x.defects > 0 ORDER BY priority_rank, x.material_id;
