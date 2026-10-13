-- Which suppliers contribute most to inbound delays?
WITH d AS (
  SELECT p.supplier_id, MAX(0, julianday(date(i.arrival_ts)) - julianday(date(p.requested_delivery_date))) AS delay_days
  FROM inbound_deliveries i JOIN po_lines l USING(po_line_id) JOIN purchase_orders p USING(po_id)
), s AS (
  SELECT supplier_id, COUNT(*) AS deliveries, SUM(delay_days > 0) AS late_deliveries, SUM(delay_days) AS total_delay_days, AVG(delay_days) AS avg_delay_days
  FROM d GROUP BY supplier_id)
SELECT supplier_id, deliveries, late_deliveries, ROUND(1.0*late_deliveries/deliveries,3) AS late_rate, ROUND(total_delay_days,1) AS total_delay_days,
       ROUND(100.0*total_delay_days/SUM(total_delay_days) OVER (),1) AS pct_of_all_delay_days,
       RANK() OVER (ORDER BY total_delay_days DESC) AS delay_rank
FROM s ORDER BY delay_rank;
