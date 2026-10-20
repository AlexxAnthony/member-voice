-- Did a release make things worse? Rating by app version vs the version before it.
CREATE OR REPLACE VIEW muzz_reviews.v_version_quality AS
WITH by_version AS (
  SELECT
    platform,
    app_version,
    MIN(review_date)                                                AS first_seen,
    COUNT(*)                                                        AS reviews,
    ROUND(AVG(rating), 2)                                           AS avg_rating,
    ROUND(SAFE_DIVIDE(COUNTIF(REGEXP_CONTAINS(stages, r'x_app_quality')), COUNT(*)), 3) AS pct_bug_mentions
  FROM muzz_reviews.v_reviews
  WHERE app_version IS NOT NULL AND app_version != ''
  GROUP BY platform, app_version
  HAVING COUNT(*) >= 30
)
SELECT
  *,
  ROUND(avg_rating - LAG(avg_rating) OVER (PARTITION BY platform ORDER BY first_seen), 2) AS rating_change_vs_previous
FROM by_version;
