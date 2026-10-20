"""
Step 3 - Build the small, aggregated files the Streamlit dashboard reads.

These mirror the BigQuery views in sql/ (same logic, computed in pandas), so the
dashboard runs without a database. Only aggregates are written - no review text -
so dashboard_data/ is safe to publish on GitHub.

Run:  python build_dashboard_data.py
In:   data/reviews_enriched.csv
Out:  dashboard_data/*.csv
"""
import json
from pathlib import Path

import pandas as pd

OUT = Path("dashboard_data")
OUT.mkdir(exist_ok=True)

STAGE_NAMES = {"1_sign_up": "1. Sign-up", "2_verification": "2. Verification", "3_profile": "3. Profile",
               "4_matching": "4. Matching", "5_messaging": "5. Messaging", "6_gold_payment": "6. Gold & payment",
               "x_trust_safety": "Trust & safety", "x_app_quality": "App quality",
               "x_support": "Customer support", "x_non_english": "Not in English"}
LIKES_LIMIT_RX = (r"used to be unlimited|unlimited|\bcap\b|limited likes|limit on likes|20 likes|more likes|"
                  r"extra likes|likes limit|likes are limited|limit the likes")

df = pd.read_csv("data/reviews_enriched.csv", dtype={"app_version": str, "gold_issue": str},
                 parse_dates=["review_date"])
df["gold_issue"] = df["gold_issue"].fillna("")
a = df[df["platform"] == "Android"].copy()          # the main sample (iOS feed was too small)
a["month"] = a["review_date"].dt.to_period("M").dt.to_timestamp()

# Headline numbers
comp = a[a["is_complaint"]]
headline = {
    "reviews": int(len(a)),
    "from": a["review_date"].min().strftime("%b %Y"),
    "to": a["review_date"].max().strftime("%b %Y"),
    "avg_rating": round(a["rating"].mean(), 2),
    "complaint_rate": round(a["is_complaint"].mean(), 3),
    "reply_rate": round(comp["developer_replied"].astype(bool).mean(), 3),
    "pct_5_star": round((a["rating"] == 5).mean(), 3),
    "pct_1_star": round((a["rating"] == 1).mean(), 3),
}
(OUT / "headline.json").write_text(json.dumps(headline, indent=2))

# Monthly health (= v_monthly_health)
monthly = a.groupby("month").agg(reviews=("rating", "size"), rating_sum=("rating", "sum"),
                                 complaints=("is_complaint", "sum")).reset_index()
monthly.to_csv(OUT / "monthly.csv", index=False)

# Friction by journey stage and month (= v_journey_friction)
st = a.assign(stage=a["stages"].str.split("|")).explode("stage")
st = st[st["stage"] != "untagged"]
friction = (st.groupby(["month", "stage"]).agg(mentions=("rating", "size"), complaint_mentions=("is_complaint", "sum"))
            .reset_index())
friction["stage_name"] = friction["stage"].map(STAGE_NAMES)
friction.to_csv(OUT / "friction.csv", index=False)

# Gold complaint reasons by month (= v_gold_issues)
gold = (comp[comp["gold_issue"] != ""].groupby(["month", "gold_issue"]).size()
        .reset_index(name="complaints"))
gold.to_csv(OUT / "gold_issues.csv", index=False)

# "Paid but still limited": mentions of a likes limit per 100 reviews, by month
lim = a["text"].str.contains(LIKES_LIMIT_RX, case=False, regex=True, na=False)
likes = a.assign(likes_limit=lim).groupby("month").agg(reviews=("rating", "size"),
                                                         mentions=("likes_limit", "sum")).reset_index()
likes.to_csv(OUT / "likes_limit.csv", index=False)

# Weekly spike detector (= v_weekly_spikes)
w = (a.groupby(a["review_date"].dt.to_period("W-SUN").dt.start_time)
     .agg(reviews=("rating", "size"), complaints=("is_complaint", "sum")).reset_index()
     .rename(columns={"review_date": "week_start"}))
if w["week_start"].iloc[-1] + pd.Timedelta(days=6) > a["review_date"].max():
    w = w.iloc[:-1]                      # drop the last, incomplete week
roll = w["complaints"].rolling(8, min_periods=4)
w["baseline"] = roll.mean().shift(1)
w["baseline_sd"] = roll.std().shift(1)
w["is_spike"] = w["complaints"] > w["baseline"] + 2 * w["baseline_sd"]
w["times_baseline"] = (w["complaints"] / w["baseline"]).round(2)
w.to_csv(OUT / "weekly.csv", index=False)

# Release quality (= v_version_quality)
v = (a[a["app_version"].fillna("") != ""].groupby("app_version")
     .agg(first_seen=("review_date", "min"), reviews=("rating", "size"), avg_rating=("rating", "mean"),
          complaint_rate=("is_complaint", "mean"))
     .query("reviews >= 30").sort_values("first_seen").reset_index())
v["rating_change"] = v["avg_rating"].diff()
v.round({"avg_rating": 3, "complaint_rate": 3, "rating_change": 3}).to_csv(OUT / "versions.csv", index=False)

print(f"Wrote {len(list(OUT.glob('*')))} files to {OUT}/")
print(json.dumps(headline, indent=2))
