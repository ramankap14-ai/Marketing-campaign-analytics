-- Decile lift table. Customers are ranked by out-of-fold model score (table `scores`),
-- decile 1 = highest predicted probability of responding.
WITH ranked AS (
    SELECT c.customer_id, c.response, s.score,
           NTILE(10) OVER (ORDER BY s.score DESC) AS decile
    FROM customers c
    JOIN scores s USING (customer_id)
),
agg AS (
    SELECT decile,
           COUNT(*)      AS customers,
           SUM(response) AS responders,
           1.0 * SUM(response) / COUNT(*) AS response_rate
    FROM ranked GROUP BY decile
),
tot AS (SELECT SUM(responders) AS r, SUM(customers) AS n FROM agg)
SELECT a.decile,
       a.customers,
       a.responders,
       ROUND(100.0 * a.response_rate, 1) AS response_rate_pct,
       ROUND(a.response_rate / (1.0 * t.r / t.n), 2) AS lift,
       ROUND(100.0 * SUM(a.responders) OVER (ORDER BY a.decile) / t.r, 1) AS cum_pct_of_responders
FROM agg a CROSS JOIN tot t
ORDER BY a.decile;
