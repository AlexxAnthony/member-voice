-- Market comparison (App Store only: Google Play reviews are not split by country).
-- Compares rates, not raw totals, and names each market's biggest pain point.
CREATE OR REPLACE VIEW muzz_reviews.v_market_compare AS
WITH market_totals AS (
  SELECT
    market,
    COUNT(*)                                                        AS reviews,
    ROUND(AVG(rating), 2)                                           AS avg_rating,
    ROUND(SAFE_DIVIDE(COUNTIF(is_complaint), COUNT(*)), 3) AS pct_complaints,
    ROUND(SAFE_DIVIDE(COUNTIF(success_story), COUNT(*)), 3)         AS pct_success_story
  FROM muzz_reviews.v_reviews
  WHERE platform = 'iOS'
  GROUP BY market
  HAVING COUNT(*) >= 30                      -- skip markets too small to compare
),
stage_pain AS (
  SELECT
    market,
    stage_name,
    COUNT(*) AS complaint_mentions,
    ROW_NUMBER() OVER (PARTITION BY market ORDER BY COUNT(*) DESC) AS rnk
  FROM muzz_reviews.v_review_stages
  WHERE platform = 'iOS' AND is_complaint AND stage != 'untagged'
  GROUP BY market, stage_name
)
SELECT
  t.*,
  p.stage_name        AS top_pain_point,
  p.complaint_mentions AS top_pain_point_mentions
FROM market_totals AS t
LEFT JOIN stage_pain AS p
  ON p.market = t.market AND p.rnk = 1;
