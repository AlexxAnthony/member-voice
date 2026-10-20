-- One row per review per journey stage it mentions (a review can mention several).
CREATE OR REPLACE VIEW muzz_reviews.v_review_stages AS
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
FROM muzz_reviews.v_reviews AS r,
UNNEST(SPLIT(r.stages, '|')) AS stage;
