-- Which warehouse zones have the longest processing times? (inbound GR->putaway, outbound pick duration)
WITH inb AS (
  SELECT CASE m.storage_condition WHEN 'Cold' THEN 'COLD' WHEN 'Controlled' THEN 'CTRL' ELSE 'AMB' END AS zone,
         (julianday(i.putaway_ts)-julianday(i.gr_ts))*24 AS gr_to_putaway_h
  FROM inbound_deliveries i JOIN po_lines l USING(po_line_id) JOIN materials m USING(material_id) WHERE i.putaway_ts IS NOT NULL),
out AS (SELECT zone, (julianday(pick_end_ts)-julianday(pick_start_ts))*24 AS pick_h FROM outbound_deliveries)
SELECT z.zone, ROUND((SELECT AVG(gr_to_putaway_h) FROM inb WHERE inb.zone=z.zone),2) AS avg_gr_to_putaway_h,
       ROUND((SELECT AVG(pick_h) FROM out WHERE out.zone=z.zone),2) AS avg_pick_h,
       (SELECT COUNT(*) FROM inb WHERE inb.zone=z.zone) AS inbound_n, (SELECT COUNT(*) FROM out WHERE out.zone=z.zone) AS outbound_n
FROM (SELECT 'AMB' AS zone UNION SELECT 'COLD' UNION SELECT 'CTRL') z ORDER BY avg_gr_to_putaway_h DESC;
