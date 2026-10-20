-- Clean, typed base view. Every other view reads from this one.
CREATE OR REPLACE VIEW `our-cursor-487813-h0.muzz_reviews.v_reviews` AS
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
FROM `our-cursor-487813-h0.muzz_reviews.reviews`
WHERE SAFE_CAST(review_date AS DATE) IS NOT NULL;

-- One row per review per journey stage it mentions (a review can mention several).
CREATE OR REPLACE VIEW `our-cursor-487813-h0.muzz_reviews.v_review_stages` AS
SELECT
  r.review_id,
  r.platform,
  r.market,
  r.review_date,
  r.review_month,
  r.rating,
  r.sentiment,
  r.sentiment_label,
  r.is_complaint,
  stage,
  CASE stage
    WHEN '1_sign_up'      THEN '1. Sign-up'
    WHEN '2_verification' THEN '2. Verification'
    WHEN '3_profile'      THEN '3. Profile'
    WHEN '4_matching'     THEN '4. Matching'
    WHEN '5_messaging'    THEN '5. Messaging'
    WHEN '6_gold_payment' THEN '6. Gold & payment'
    WHEN 'x_trust_safety' THEN 'Trust & safety'
    WHEN 'x_app_quality'  THEN 'App quality'
    WHEN 'x_support'      THEN 'Customer support'
    WHEN 'x_non_english'  THEN 'Not in English'
    ELSE 'Untagged'
  END AS stage_name
FROM `our-cursor-487813-h0.muzz_reviews.v_reviews` AS r,
UNNEST(SPLIT(r.stages, '|')) AS stage;

-- Monthly health by platform and market.
-- Counts and sums only: rates are calculated in Looker Studio so they stay
-- correct whatever filters the viewer applies.
CREATE OR REPLACE VIEW `our-cursor-487813-h0.muzz_reviews.v_monthly_health` AS
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
FROM `our-cursor-487813-h0.muzz_reviews.v_reviews`
GROUP BY review_month, platform, market;

-- Where in the member journey do complaints happen?
-- The "friction funnel": complaints (1-2 star reviews) by journey stage.
CREATE OR REPLACE VIEW `our-cursor-487813-h0.muzz_reviews.v_journey_friction` AS
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
FROM `our-cursor-487813-h0.muzz_reviews.v_review_stages`
WHERE stage != 'untagged'
GROUP BY review_month, platform, market, stage, stage_name;

-- Why are members unhappy about Gold? Complaints (1-2 stars) that mention
-- Gold or payment, by reason and month.
CREATE OR REPLACE VIEW `our-cursor-487813-h0.muzz_reviews.v_gold_issues` AS
SELECT
  review_month,
  platform,
  gold_issue,
  COUNT(*)                                   AS complaints,
  SUM(rating)                                AS rating_sum
FROM `our-cursor-487813-h0.muzz_reviews.v_reviews`
WHERE is_complaint AND gold_issue IS NOT NULL
GROUP BY review_month, platform, gold_issue;

-- Spike detector: flags any week where complaints run more than 2 standard
-- deviations above the previous 8 weeks. It caught the late-May outage.
CREATE OR REPLACE VIEW `our-cursor-487813-h0.muzz_reviews.v_weekly_spikes` AS
WITH weekly AS (
  SELECT
    DATE_TRUNC(review_date, WEEK(MONDAY))    AS week_start,
    COUNT(*)                                 AS reviews,
    COUNTIF(is_complaint)                    AS complaints
  FROM `our-cursor-487813-h0.muzz_reviews.v_reviews`
  WHERE platform = 'Android'
  GROUP BY week_start
),
with_baseline AS (
  SELECT
    *,
    AVG(complaints)    OVER w AS baseline_complaints,
    STDDEV(complaints) OVER w AS baseline_sd,
    COUNT(*)           OVER w AS weeks_in_baseline
  FROM weekly
  WINDOW w AS (ORDER BY week_start ROWS BETWEEN 8 PRECEDING AND 1 PRECEDING)
)
SELECT
  week_start,
  reviews,
  complaints,
  ROUND(baseline_complaints, 1)                                        AS baseline_complaints,
  ROUND(SAFE_DIVIDE(complaints, baseline_complaints), 2)               AS times_baseline,
  weeks_in_baseline >= 4
    AND complaints > baseline_complaints + 2 * baseline_sd             AS is_spike
FROM with_baseline;

-- How often do unhappy Android reviewers get a reply from Muzz?
-- Reply *rate* only: Google Play dates a review by its last edit, so the time
-- between review and reply is not reliable and is left out on purpose.
CREATE OR REPLACE VIEW `our-cursor-487813-h0.muzz_reviews.v_reply_performance` AS
SELECT
  review_month,
  COUNT(*)                                                          AS complaints,
  COUNTIF(developer_replied)                                        AS replied,
  ROUND(SAFE_DIVIDE(COUNTIF(developer_replied), COUNT(*)), 3)       AS reply_rate
FROM `our-cursor-487813-h0.muzz_reviews.v_reviews`
WHERE platform = 'Android' AND is_complaint
GROUP BY review_month;

-- Did a release make things worse? Rating by app version vs the version before it.
CREATE OR REPLACE VIEW `our-cursor-487813-h0.muzz_reviews.v_version_quality` AS
WITH by_version AS (
  SELECT
    platform,
    app_version,
    MIN(review_date)                                                AS first_seen,
    COUNT(*)                                                        AS reviews,
    ROUND(AVG(rating), 2)                                           AS avg_rating,
    ROUND(SAFE_DIVIDE(COUNTIF(REGEXP_CONTAINS(stages, r'x_app_quality')), COUNT(*)), 3) AS pct_bug_mentions
  FROM `our-cursor-487813-h0.muzz_reviews.v_reviews`
  WHERE app_version IS NOT NULL AND app_version != ''
  GROUP BY platform, app_version
  HAVING COUNT(*) >= 30
)
SELECT
  *,
  ROUND(avg_rating - LAG(avg_rating) OVER (PARTITION BY platform ORDER BY first_seen), 2) AS rating_change_vs_previous
FROM by_version;
