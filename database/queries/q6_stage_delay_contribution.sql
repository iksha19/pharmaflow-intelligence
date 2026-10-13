-- Which outbound stages contribute most to order delay? Average hours per stage, split by on-time vs late.
WITH s AS (
  SELECT (o.dispatch_ts > c.requested_dispatch_ts) AS late,
    (julianday(o.allocation_ts)-julianday(c.order_ts))*24 AS wait_allocation,
    (julianday(o.pick_start_ts)-julianday(o.allocation_ts))*24 AS wait_pick,
    (julianday(o.pick_end_ts)-julianday(o.pick_start_ts))*24 AS picking,
    (julianday(o.pack_start_ts)-julianday(o.pick_end_ts))*24 AS wait_pack,
    (julianday(o.pack_end_ts)-julianday(o.pack_start_ts))*24 AS packing,
    (julianday(o.dispatch_ts)-julianday(o.pack_end_ts))*24 AS wait_dispatch
  FROM outbound_deliveries o JOIN customer_orders c USING(order_id)),
u AS (SELECT late, 'wait_allocation' AS stage, wait_allocation AS h FROM s UNION ALL SELECT late,'wait_pick',wait_pick FROM s
      UNION ALL SELECT late,'picking',picking FROM s UNION ALL SELECT late,'wait_pack',wait_pack FROM s
      UNION ALL SELECT late,'packing',packing FROM s UNION ALL SELECT late,'wait_dispatch',wait_dispatch FROM s)
SELECT stage, ROUND(AVG(h),2) AS avg_h_all, ROUND(AVG(CASE WHEN late=1 THEN h END),2) AS avg_h_late_orders, ROUND(AVG(CASE WHEN late=0 THEN h END),2) AS avg_h_on_time_orders,
       ROUND(AVG(CASE WHEN late=1 THEN h END)-AVG(CASE WHEN late=0 THEN h END),2) AS late_minus_ontime_h
FROM u GROUP BY stage ORDER BY late_minus_ontime_h DESC;
