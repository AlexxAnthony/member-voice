-- Why are members unhappy about Gold? Complaints (1-2 stars) that mention
-- Gold or payment, by reason and month.
CREATE OR REPLACE VIEW muzz_reviews.v_gold_issues AS
SELECT
  review_month,
  platform,
  gold_issue,
  COUNT(*)                                   AS complaints,
  SUM(rating)                                AS rating_sum
FROM muzz_reviews.v_reviews
WHERE is_complaint AND gold_issue IS NOT NULL
GROUP BY review_month, platform, gold_issue;
