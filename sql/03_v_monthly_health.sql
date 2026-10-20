-- Monthly health by platform and market.
-- Counts and sums only: rates are calculated in Looker Studio so they stay
-- correct whatever filters the viewer applies.
CREATE OR REPLACE VIEW muzz_reviews.v_monthly_health AS
SELECT
  review_month,
  platform,
  market,
  COUNT(*)                                   AS reviews,
  SUM(rating)                                AS rating_sum,
  SUM(sentiment)                             AS sentiment_sum,
  COUNTIF(is_complaint)      AS complaints,
  COUNTIF(rating = 1)                        AS one_star_reviews,
  COUNTIF(rating >= 4)                       AS four_plus_reviews,
  COUNTIF(success_story)                     AS success_story_reviews
FROM muzz_reviews.v_reviews
GROUP BY review_month, platform, market;
