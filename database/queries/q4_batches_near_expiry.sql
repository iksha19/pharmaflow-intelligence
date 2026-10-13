-- Which batches are approaching expiry? (:snapshot ISO date; window 90 days)
SELECT b.batch_id, b.material_id, m.category, b.stock_status, b.recorded_qty,
       ROUND(b.recorded_qty*m.unit_cost,0) AS value_at_risk, date(b.expiry_date) AS expiry_date,
       CAST(julianday(date(b.expiry_date)) - julianday(date(:snapshot)) AS INTEGER) AS days_to_expiry,
       CASE WHEN date(b.expiry_date) <= date(:snapshot) THEN 'EXPIRED' WHEN date(b.expiry_date) <= date(:snapshot,'+30 day') THEN '<=30d' ELSE '31-90d' END AS bucket
FROM inventory_batches b JOIN materials m USING(material_id)
WHERE b.recorded_qty > 0 AND b.stock_status <> 'Rejected' AND date(b.expiry_date) <= date(:snapshot,'+90 day')
ORDER BY value_at_risk DESC LIMIT 100;
