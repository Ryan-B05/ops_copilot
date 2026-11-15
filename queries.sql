-- ============================================================
-- Ops Copilot: reference queries
-- Ten business questions, hand written and verified.
-- These are the ground truth for the evaluation set.
--
-- All data is synthetic. PostgreSQL 18.
-- ============================================================


-- ------------------------------------------------------------
-- Q1. How many collections did we do last month?
--
-- Note: 'collected' excludes contaminated lifts. A contaminated
-- bin was still emptied, so the alternative reading is
-- status IN ('collected','contaminated'). Chosen the narrower
-- definition deliberately.
-- ------------------------------------------------------------
SELECT COUNT(*) AS collections_last_month
FROM collections
WHERE status = 'collected'
  AND collected_at >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'
  AND collected_at <  date_trunc('month', CURRENT_DATE);


-- ------------------------------------------------------------
-- Q2. How many customers do we have of each account type?
--
-- Counts all customers including inactive ones. Add
-- WHERE status = 'active' for the live figure.
-- ------------------------------------------------------------
SELECT account_type,
       COUNT(*) AS customers
FROM customers
GROUP BY account_type
ORDER BY customers DESC;


-- ------------------------------------------------------------
-- Q3. What is the average weight of a collection, by bin type?
--
-- AVG ignores NULLs, so missed collections are excluded
-- automatically. This is why weight_kg is nullable rather
-- than defaulting to zero.
-- ------------------------------------------------------------
SELECT bin_type,
       ROUND(AVG(weight_kg), 2) AS avg_weight_kg,
       COUNT(weight_kg)         AS weighed_collections
FROM collections
GROUP BY bin_type
ORDER BY avg_weight_kg DESC;


-- ------------------------------------------------------------
-- Q4. What was the total tonnage collected on each route in
--     the last 3 complete months?
--
-- Weight is stored in kilos, so it is converted to tonnes.
-- Grouped on the key as well as the name.
-- ------------------------------------------------------------
SELECT r.name                              AS route,
       ROUND(SUM(c.weight_kg) / 1000.0, 2) AS tonnes
FROM collections c
JOIN routes r ON r.route_id = c.route_id
WHERE c.status = 'collected'
  AND c.collected_at >= date_trunc('month', CURRENT_DATE) - INTERVAL '3 months'
  AND c.collected_at <  date_trunc('month', CURRENT_DATE)
GROUP BY r.route_id, r.name
ORDER BY tonnes DESC;


-- ------------------------------------------------------------
-- Q5. Top 10 customers by total tonnage this year.
--
-- Filtered to the current year and converted to tonnes.
-- Grouped on customer_id as well as name, because names are
-- not unique. Two customers can share a name and must not
-- be merged into one row.
-- ------------------------------------------------------------
SELECT cu.customer_id,
       cu.name                             AS customer,
       ROUND(SUM(c.weight_kg) / 1000.0, 2) AS tonnes
FROM collections c
JOIN customers cu ON cu.customer_id = c.customer_id
WHERE c.status = 'collected'
  AND c.collected_at >= date_trunc('year', CURRENT_DATE)
GROUP BY cu.customer_id, cu.name
ORDER BY tonnes DESC
LIMIT 10;


-- ------------------------------------------------------------
-- Q6. Which customers have had more than 3 missed collections
--     in the last 90 days?
--
-- More than 3 means > 3, not >= 3. The window is a rolling
-- 90 days, not 3 calendar months.
-- WHERE filters the rows, HAVING filters the groups.
-- ------------------------------------------------------------
SELECT cu.customer_id,
       cu.name       AS customer,
       COUNT(*)      AS missed_collections
FROM collections c
JOIN customers cu ON cu.customer_id = c.customer_id
WHERE c.status = 'missed'
  AND c.collected_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY cu.customer_id, cu.name
HAVING COUNT(*) > 3
ORDER BY missed_collections DESC;


-- ------------------------------------------------------------
-- Q7. How many invoices are currently overdue, and what do
--     they total?
--
-- Overdue is derived, not stored. This is why the status
-- column was removed from the invoices table.
-- ------------------------------------------------------------
SELECT COUNT(*)          AS overdue_invoices,
       SUM(amount_eur)   AS overdue_total_eur
FROM invoices
WHERE paid_at IS NULL
  AND due_at < CURRENT_DATE;


-- ------------------------------------------------------------
-- Q8. Which active customers have had no collection at all in
--     the last 30 days?
--
-- The date condition belongs in the ON clause, not the WHERE.
-- In the WHERE it would filter after the join and discard the
-- NULL rows that represent the absence being looked for,
-- returning nothing every time.
-- ------------------------------------------------------------
SELECT cu.customer_id,
       cu.name AS customer
FROM customers cu
LEFT JOIN collections c
       ON c.customer_id = cu.customer_id
      AND c.collected_at >= CURRENT_DATE - INTERVAL '30 days'
WHERE c.collection_id IS NULL
  AND cu.status = 'active'
ORDER BY cu.customer_id;


-- ------------------------------------------------------------
-- Q9. Contamination rate per route, as a percentage,
--     worst first.
--
-- 100.0 forces numeric division rather than integer division.
-- NULLIF guards against dividing by zero if a route had no
-- collections at all.
-- ------------------------------------------------------------
SELECT r.name AS route,
       COUNT(*) FILTER (WHERE c.status = 'contaminated') AS contaminated,
       COUNT(*)                                          AS total,
       ROUND(
           COUNT(*) FILTER (WHERE c.status = 'contaminated') * 100.0
           / NULLIF(COUNT(*), 0), 2
       ) AS contamination_rate_pct
FROM collections c
JOIN routes r ON r.route_id = c.route_id
GROUP BY r.route_id, r.name
ORDER BY contamination_rate_pct DESC;


-- ------------------------------------------------------------
-- Q10. Total tonnage per month for the last 6 complete months,
--      oldest first.
--
-- The current month is excluded. A partial month sitting
-- beside complete ones reads as a collapse in volume.
-- date_trunc returns a timestamp, so it is cast to a date.
-- ------------------------------------------------------------
SELECT date_trunc('month', collected_at)::date AS month,
       ROUND(SUM(weight_kg) / 1000.0, 2)       AS tonnes
FROM collections
WHERE status = 'collected'
  AND collected_at >= date_trunc('month', CURRENT_DATE) - INTERVAL '6 months'
  AND collected_at <  date_trunc('month', CURRENT_DATE)
GROUP BY 1
ORDER BY month;
