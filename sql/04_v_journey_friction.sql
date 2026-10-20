-- Where in the member journey do complaints happen?
-- The "friction funnel": complaints (1-2 star reviews) by journey stage.
CREATE OR REPLACE VIEW muzz_reviews.v_journey_friction AS
SELECT
  review_month,
  platform,
  market,
  stage,
  stage_name,
  COUNT(*)                                   AS mentions,
  COUNTIF(is_complaint)      AS complaint_mentions,
  SUM(sentiment)                             AS sentiment_sum,
  SUM(rating)                                AS rating_sum
FROM muzz_reviews.v_review_stages
WHERE stage != 'untagged'
GROUP BY review_month, platform, market, stage, stage_name;
