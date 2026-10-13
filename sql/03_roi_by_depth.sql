-- Profit if we contact only the top N deciles vs. everyone.
-- Assumptions (from the dataset's own constants Z_CostContact / Z_Revenue):
--   cost per contact = 3, revenue per responder = 11  ->  break-even response rate = 27.3%
WITH ranked AS (
    SELECT c.response, NTILE(10) OVER (ORDER BY s.score DESC) AS decile
    FROM customers c JOIN scores s USING (customer_id)
),
agg AS (
    SELECT decile, COUNT(*) AS contacts, SUM(response) AS responders
    FROM ranked GROUP BY decile
)
SELECT decile                                              AS top_n_deciles_contacted,
       SUM(contacts)   OVER (ORDER BY decile)              AS contacts,
       SUM(responders) OVER (ORDER BY decile)              AS responders,
       SUM(responders) OVER (ORDER BY decile) * 11         AS revenue,
       SUM(contacts)   OVER (ORDER BY decile) * 3          AS cost,
       SUM(responders) OVER (ORDER BY decile) * 11
         - SUM(contacts) OVER (ORDER BY decile) * 3        AS profit
FROM agg
ORDER BY decile;
