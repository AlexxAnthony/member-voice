"""
Step 2b (optional) - Print the headline numbers locally, before BigQuery.

Run:  python summarise.py
"""
import pandas as pd

df = pd.read_csv("data/reviews_enriched.csv", dtype={"app_version": str, "gold_issue": str},
                 parse_dates=["review_date"])
df["gold_issue"] = df["gold_issue"].fillna("")
STAGE_NAMES = {"1_sign_up": "1. Sign-up", "2_verification": "2. Verification", "3_profile": "3. Profile",
               "4_matching": "4. Matching", "5_messaging": "5. Messaging", "6_gold_payment": "6. Gold & payment",
               "x_trust_safety": "Trust & safety", "x_app_quality": "App quality",
               "x_support": "Customer support", "x_non_english": "Not in English", "untagged": "Untagged"}

android = df[df["platform"] == "Android"]
print(f"Reviews: {len(df):,}  ({df['review_date'].min():%b %Y} to {df['review_date'].max():%b %Y})")
print(df.groupby(["platform", "market"]).size().to_string(), "\n")

print("== Overall (Android, the main sample)")
print(f"Average rating of written reviews: {android['rating'].mean():.2f}")
print(f"Rating split: {android['rating'].value_counts(normalize=True).sort_index().round(2).to_dict()}")
print(f"Complaints (1-2 stars): {android['is_complaint'].mean():.0%}")
print(f"Mention meeting a partner / marriage: {android['success_story'].mean():.1%}\n")

print("== Friction: share of complaints that mention each stage (a complaint can mention several)")
comp = df[df["is_complaint"]]
st = comp.assign(stage=comp["stages"].str.split("|")).explode("stage")
print((st["stage"].value_counts() / len(comp)).rename(index=STAGE_NAMES).round(3).to_string(), "\n")

print("== Why members complain about Gold")
gold = comp[comp["gold_issue"] != ""]
print(f"{len(gold)} complaints mention Gold or payment")
print(gold["gold_issue"].value_counts(normalize=True).round(3).to_string(), "\n")

print("== Spike weeks (complaints > previous 8-week average + 2 SD)")
w = android.groupby(android["review_date"].dt.to_period("W")).agg(reviews=("rating", "size"),
                                                                   complaints=("is_complaint", "sum"))
base = w["complaints"].rolling(8, min_periods=4)
w["baseline"] = base.mean().shift(1).round(1)
w["times_baseline"] = (w["complaints"] / w["baseline"]).round(2)
spikes = w[w["complaints"] > w["baseline"] + 2 * base.std().shift(1)]
print(spikes.to_string() if len(spikes) else "None", "\n")

print("== App versions (30+ reviews), oldest first")
v = (android[android["app_version"].fillna("") != ""].groupby("app_version")
     .agg(first_seen=("review_date", "min"), reviews=("rating", "size"), avg_rating=("rating", "mean"),
          pct_complaints=("is_complaint", "mean"))
     .query("reviews >= 30").sort_values("first_seen"))
v["change_vs_previous"] = v["avg_rating"].diff()
print(v.round({"avg_rating": 2, "pct_complaints": 2, "change_vs_previous": 2}).to_string(), "\n")

print("== Monthly trend (Android)")
m = android.groupby(android["review_date"].dt.to_period("M")).agg(
    reviews=("rating", "size"), avg_rating=("rating", "mean"), pct_complaints=("is_complaint", "mean"))
print(m.round(2).to_string(), "\n")

low = android[android["is_complaint"]]
print(f"== Muzz replied to {low['developer_replied'].astype(bool).mean():.0%} of Android complaints")
