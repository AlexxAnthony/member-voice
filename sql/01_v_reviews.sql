-- Clean, typed base view. Every other view reads from this one.
CREATE OR REPLACE VIEW muzz_reviews.v_reviews AS
SELECT
  review_id,
  platform,
  market,
  SAFE_CAST(review_date AS DATE)                         AS review_date,
  DATE_TRUNC(SAFE_CAST(review_date AS DATE), MONTH)      AS review_month,
  rating,
  sentiment,
  sentiment_label,
  is_complaint,
  stages,
  NULLIF(gold_issue, '')                                AS gold_issue,
  success_story,
  CAST(app_version AS STRING)                            AS app_version,
  thumbs_up,
  developer_replied,
  SAFE_CAST(reply_date AS DATE)                          AS reply_date,
  word_count,
  text
FROM muzz_reviews.reviews
WHERE SAFE_CAST(review_date AS DATE) IS NOT NULL;
