-- How often do unhappy Android reviewers get a reply from Muzz?
-- Reply *rate* only: Google Play dates a review by its last edit, so the time
-- between review and reply is not reliable and is left out on purpose.
CREATE OR REPLACE VIEW muzz_reviews.v_reply_performance AS
SELECT
  review_month,
  COUNT(*)                                                          AS complaints,
  COUNTIF(developer_replied)                                        AS replied,
  ROUND(SAFE_DIVIDE(COUNTIF(developer_replied), COUNT(*)), 3)       AS reply_rate
FROM muzz_reviews.v_reviews
WHERE platform = 'Android' AND is_complaint
GROUP BY review_month;
