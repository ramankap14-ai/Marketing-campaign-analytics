-- Response rate by segment. Each row: segment type, segment value, customers, responders, response rate, avg spend.
-- Break-even response rate = cost per contact / revenue per response = 3 / 11 = 27.3%

SELECT 'prior_campaigns_accepted' AS segment_type, CAST(prior_accepted AS TEXT) AS segment,
       COUNT(*) AS customers, SUM(response) AS responders,
       ROUND(100.0 * AVG(response), 1) AS response_rate_pct, ROUND(AVG(total_spend), 0) AS avg_spend
FROM customers GROUP BY prior_accepted

UNION ALL
SELECT 'income_quartile', income_band, COUNT(*), SUM(response),
       ROUND(100.0 * AVG(response), 1), ROUND(AVG(total_spend), 0)
FROM customers GROUP BY income_band

UNION ALL
SELECT 'spend_quartile', spend_band, COUNT(*), SUM(response),
       ROUND(100.0 * AVG(response), 1), ROUND(AVG(total_spend), 0)
FROM customers GROUP BY spend_band

UNION ALL
SELECT 'recency_bucket',
       CASE WHEN recency_days <= 20 THEN '0-20 days'
            WHEN recency_days <= 40 THEN '21-40 days'
            WHEN recency_days <= 60 THEN '41-60 days'
            WHEN recency_days <= 80 THEN '61-80 days'
            ELSE '81+ days' END,
       COUNT(*), SUM(response), ROUND(100.0 * AVG(response), 1), ROUND(AVG(total_spend), 0)
FROM customers GROUP BY 2

UNION ALL
SELECT 'children_at_home', CAST(children AS TEXT), COUNT(*), SUM(response),
       ROUND(100.0 * AVG(response), 1), ROUND(AVG(total_spend), 0)
FROM customers GROUP BY children

UNION ALL
SELECT 'education', education, COUNT(*), SUM(response),
       ROUND(100.0 * AVG(response), 1), ROUND(AVG(total_spend), 0)
FROM customers GROUP BY education

UNION ALL
SELECT 'marital_status', marital_status, COUNT(*), SUM(response),
       ROUND(100.0 * AVG(response), 1), ROUND(AVG(total_spend), 0)
FROM customers GROUP BY marital_status
ORDER BY 1, 2;
