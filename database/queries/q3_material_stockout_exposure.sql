-- Which materials have the highest stockout exposure?
SELECT c.material_id, m.material_name, COUNT(*) AS orders, SUM(o.stockout_flag) AS stockout_orders,
       ROUND(1.0*SUM(o.stockout_flag)/COUNT(*),3) AS stockout_rate, SUM(o.qty_backordered) AS backordered_qty,
       ROUND(SUM(o.qty_backordered*m.unit_cost),0) AS backorder_value,
       RANK() OVER (ORDER BY SUM(o.qty_backordered*m.unit_cost) DESC) AS exposure_rank
FROM outbound_deliveries o JOIN customer_orders c USING(order_id) JOIN materials m ON m.material_id=c.material_id
GROUP BY c.material_id HAVING COUNT(*) >= 5 ORDER BY exposure_rank LIMIT 20;
