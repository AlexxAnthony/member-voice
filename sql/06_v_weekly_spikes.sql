-- Spike detector: flags any week where complaints run more than 2 standard
-- deviations above the previous 8 weeks. It caught the late-May outage.
CREATE OR REPLACE VIEW muzz_reviews.v_weekly_spikes AS
WITH weekly AS (
  SELECT
    DATE_TRUNC(review_date, WEEK(MONDAY))    AS week_start,
    COUNT(*)                                 AS reviews,
    COUNTIF(is_complaint)                    AS complaints
  FROM muzz_reviews.v_reviews
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
