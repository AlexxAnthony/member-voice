-- India vs every other market, before and after the April 2026 launch.
CREATE OR REPLACE VIEW muzz_reviews.v_india_launch AS
SELECT
  IF(market = 'IN', 'India', 'Other App Store markets')            AS market_group,
  india_launch_period,
  COUNT(*)                                                          AS reviews,
  ROUND(AVG(rating), 2)                                             AS avg_rating,
  ROUND(AVG(sentiment), 3)                                          AS avg_sentiment,
  ROUND(SAFE_DIVIDE(COUNTIF(is_complaint), COUNT(*)), 3) AS pct_complaints
FROM muzz_reviews.v_reviews
WHERE platform = 'iOS'
GROUP BY market_group, india_launch_period;
