# Guide: BigQuery and Looker Studio

About 60-90 minutes the first time. Everything here is free and needs only a Google account, no card.

## Part 1 - Load the data into BigQuery

1. Go to [console.cloud.google.com/bigquery](https://console.cloud.google.com/bigquery). Accept the terms. This gives you the free **BigQuery sandbox**.
2. Create a project if asked, e.g. `member-voice`.
3. In the Explorer panel, click the three dots next to your project, then **Create dataset**.
   - Dataset ID: `muzz_reviews`
   - Location: `europe-west2 (London)`
4. Click the three dots next to `muzz_reviews`, then **Create table**.
   - Create table from: **Upload**, then choose `data/reviews_enriched.csv`
   - File format: CSV
   - Table: `reviews`
   - Schema: switch on **Edit as text**, and paste the whole of `schema.json`
   - Advanced options: **Header rows to skip = 1** and tick **Allow quoted newlines**. Some reviews contain line breaks, so this one matters.
5. Open a new query tab. Paste and run each file in `sql/` **in order, 01 to 08**. Each one creates a view.
6. Sanity check:
   ```sql
   SELECT platform, COUNT(*) AS reviews, ROUND(AVG(rating), 2) AS avg_rating
   FROM muzz_reviews.v_reviews
   GROUP BY platform;
   ```

> **Sandbox limit:** tables in the free sandbox expire after 60 days. That's fine for an interview process. If you want the dashboard to last longer, use Looker Studio's **Extracted data** connector for each source (step 3 below), or add billing (it stays within the free tier).

## Part 2 - Build the dashboard in Looker Studio

1. Go to [lookerstudio.google.com](https://lookerstudio.google.com), then **Create**, then **Report**.
2. Choose **BigQuery**, then your project, then `muzz_reviews`, then `v_monthly_health`. Click **Add**.
3. Use **Resource**, then **Manage added data sources**, then **Add a data source** to add the other five views too: `v_journey_friction`, `v_gold_issues`, `v_weekly_spikes`, `v_reply_performance` and `v_version_quality`.

### Calculated fields

The views hold counts and sums, and the rates are calculated here. That way they stay correct whatever filter someone picks, which is a good point to make in the interview.

In **v_monthly_health**, use **Resource**, then **Manage added data sources**, then **Edit**, then **Add a field**:

| Field name | Formula | Format |
| --- | --- | --- |
| Avg rating | `SUM(rating_sum) / SUM(reviews)` | Number, 2 decimals |
| Complaint rate | `SUM(complaints) / SUM(reviews)` | Percent |
| Success story rate | `SUM(success_story_reviews) / SUM(reviews)` | Percent |
| Avg sentiment | `SUM(sentiment_sum) / SUM(reviews)` | Number, 2 decimals |

In **v_journey_friction**:

| Field name | Formula | Format |
| --- | --- | --- |
| Complaint share of mentions | `SUM(complaint_mentions) / SUM(mentions)` | Percent |

### Page 1 - Member health
- **Controls** across the top: a date range control (on `review_month`) and a drop-down list for `platform`. These make it self-service.
- **Scorecards:** reviews, Avg rating, Complaint rate, Success story rate. Turn on "Comparison date range: previous period".
- **Time series:** `review_month` against Complaint rate and Avg rating (right axis).
- **Annotation:** add a text box on the chart marking May 2026 as "Outage, 25-31 May".

### Page 2 - Where members get stuck (the friction funnel)
- **Bar chart** from `v_journey_friction`. Dimension: `stage_name`. Metric: `complaint_mentions`. Sort by `stage_name` ascending so the bars follow the member journey from sign-up to Gold.
- **Pivot table with heatmap.** Rows: `stage_name`. Columns: `review_month`. Metric: `complaint_mentions`. This shows when each stage flared up.
- **Table.** `stage_name`, `mentions`, Complaint share of mentions.

### Page 3 - Gold and spikes
- **Bar chart** from `v_gold_issues`. Dimension: `gold_issue`. Metric: `complaints`. Sort descending.
- **Stacked column chart** from `v_gold_issues`. Dimension: `review_month`. Breakdown: `gold_issue`. Metric: `complaints`. You'll see "Paid but still limited" appear from June 2026.
- **Combo chart** from `v_weekly_spikes`: `week_start` with `complaints` as bars and `baseline_complaints` as a line. Then add a table filtered to `is_spike = true`.

### Page 4 - Operations
- **Time series** from `v_reply_performance`: `reply_rate` by month.
- **Table** from `v_version_quality`. Add conditional formatting so `rating_change_vs_previous` shows red when below 0 and green when above 0.

### Share it
1. Use **Share**, then **Manage access**, then **Anyone with the link: Viewer**.
2. Check each data source uses **Owner's credentials** (this is the default), so viewers don't need BigQuery access.
3. Put the link in the README and on your portfolio.

## Talking points this gives you
- "I loaded the data into BigQuery with an explicit schema rather than autodetect, because autodetect turned app version 6.10 into 6.1."
- "I aggregate counts in SQL and calculate rates in Looker Studio, so the numbers stay right under any filter."
- "Every view builds on one base view, so the cleaning rules live in one place."
- "My spike detector compares each week with the 8 weeks before it, and it caught the May outage without me telling it where to look."
