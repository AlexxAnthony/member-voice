"""
Member Voice - Streamlit dashboard.

Reads the aggregated files in dashboard_data/ (built by build_dashboard_data.py),
so it runs anywhere without a database. Run locally with:  streamlit run app.py
"""
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).parent / "dashboard_data"
STORE_RATING = 4.26        # Google Play rating when the reviews were collected (20 Oct 2026)

# Colours: one highlight, one neutral for context, one reserved for "something went wrong".
BLUE, GREY, RED = "#2a78d6", "#c9c7bf", "#e34948"
INK, INK_2 = "#0b0b0b", "#52514e"
JOURNEY = ["1. Sign-up", "2. Verification", "3. Profile", "4. Matching", "5. Messaging",
           "6. Gold & payment", "Trust & safety", "App quality", "Customer support"]

st.set_page_config(page_title="Member Voice", page_icon="💬", layout="wide")


@st.cache_data
def load():
    h = json.loads((DATA / "headline.json").read_text())
    p = {"parse_dates": ["month"]}
    return (h,
            pd.read_csv(DATA / "monthly.csv", **p),
            pd.read_csv(DATA / "friction.csv", **p),
            pd.read_csv(DATA / "gold_issues.csv", **p),
            pd.read_csv(DATA / "likes_limit.csv", **p),
            pd.read_csv(DATA / "weekly.csv", parse_dates=["week_start"]),
            pd.read_csv(DATA / "versions.csv", parse_dates=["first_seen"]))


headline, monthly, friction, gold, likes, weekly, versions = load()


def style(fig, height=360, y_title=None, pct=False):
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=8, b=8), plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Inter, Arial, sans-serif", size=13, color=INK_2), showlegend=False,
        hoverlabel=dict(bgcolor="white", font_color=INK), bargap=0.25)
    fig.update_xaxes(showgrid=False, linecolor="#e4e2dc", ticks="")
    fig.update_yaxes(gridcolor="#efeee9", zeroline=False, title=y_title,
                     tickformat=".0%" if pct else None)
    return fig


CHART_CONFIG = {"displayModeBar": False}

# ---------------------------------------------------------------- header
st.title("Member Voice")
st.markdown(f"#### What {headline['reviews']:,} public Google Play reviews say about the Muzz member journey")
st.caption(f"Independent analysis of public reviews, {headline['from']} to {headline['to']}. "
           "Not affiliated with or endorsed by Muzz. No reviewer names or profile details are stored. "
           "[Code on GitHub](https://github.com/AlexxAnthony/member-voice)")

months = sorted(monthly["month"].dt.to_period("M").unique())
start, end = st.select_slider("Months shown", options=months, value=(months[0], months[-1]),
                              format_func=lambda p: p.strftime("%b %Y"))
s, e = start.to_timestamp(), end.to_timestamp()
in_range = lambda d, col="month": d[(d[col] >= s) & (d[col] <= e)]
m, fr, gd, lk = in_range(monthly), in_range(friction), in_range(gold), in_range(likes)
wk = weekly[(weekly["week_start"] >= s) & (weekly["week_start"] < e + pd.offsets.MonthEnd(1) + pd.Timedelta(days=1))]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Reviews in view", f"{m['reviews'].sum():,}")
c2.metric("Avg rating of written reviews", f"{m['rating_sum'].sum() / m['reviews'].sum():.2f}")
c2.caption(f"Compared with {STORE_RATING} overall on the Play Store")
c3.metric("Complaints (1-2 stars)", f"{m['complaints'].sum() / m['reviews'].sum():.0%}")
c4.metric("Complaints Muzz replied to", f"{headline['reply_rate']:.0%}")
c4.caption("Across the whole sample")

st.divider()

# ---------------------------------------------------------------- 1. friction
st.subheader("1. Gold is where frustration concentrates, not onboarding")
st.caption("Share of complaints (1-2 star reviews) that mention each stage of the member journey. "
           "A complaint can mention several stages, so bars don't add up to 100%.")
total_complaints = m["complaints"].sum()
stage_share = (fr.groupby("stage_name")["complaint_mentions"].sum() / total_complaints).reindex(JOURNEY).fillna(0)
fig = go.Figure(go.Bar(
    y=stage_share.index, x=stage_share.values, orientation="h",
    marker=dict(color=[BLUE if n == "6. Gold & payment" else GREY for n in stage_share.index],
                cornerradius=4),
    text=[f"{v:.0%}" for v in stage_share.values], textposition="outside", cliponaxis=False,
    textfont=dict(color=INK),
    hovertemplate="%{y}: %{x:.1%} of complaints<extra></extra>"))
style(fig, height=380)
fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
fig.update_xaxes(tickformat=".0%", showticklabels=False, range=[0, stage_share.max() * 1.15])
st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)

# ---------------------------------------------------------------- 2. gold
st.subheader("2. \"I paid and I'm still limited\" appeared in June 2026")
left, right = st.columns(2)
with left:
    st.caption("Why complaints mention Gold (where a specific reason was found)")
    reasons = gd[gd["gold_issue"] != "Other Gold mention"].groupby("gold_issue")["complaints"].sum().sort_values()
    other = gd.loc[gd["gold_issue"] == "Other Gold mention", "complaints"].sum()
    fig = go.Figure(go.Bar(
        y=reasons.index, x=reasons.values, orientation="h",
        marker=dict(color=[BLUE if r == "Paid but still limited" else GREY for r in reasons.index], cornerradius=4),
        text=reasons.values, textposition="outside", cliponaxis=False, textfont=dict(color=INK),
        hovertemplate="%{y}: %{x} complaints<extra></extra>"))
    style(fig, height=320)
    fig.update_xaxes(showticklabels=False, range=[0, reasons.max() * 1.18])
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
    st.caption(f"A further {other:,} Gold complaints didn't match a specific reason.")
with right:
    st.caption("Reviews mentioning a limit on likes, per 100 reviews")
    per100 = lk["mentions"] / lk["reviews"] * 100
    fig = go.Figure(go.Scatter(
        x=lk["month"], y=per100, mode="lines+markers", line=dict(color=BLUE, width=2),
        marker=dict(size=8, color=BLUE, line=dict(color="white", width=2)),
        hovertemplate="%{x|%b %Y}: %{y:.1f} per 100 reviews<extra></extra>"))
    style(fig, height=320)
    if len(per100):
        peak = per100.idxmax()
        fig.add_annotation(x=lk.loc[peak, "month"], y=per100[peak], text=f"{per100[peak]:.1f} in {lk.loc[peak, 'month']:%b %Y}",
                           showarrow=False, yshift=16, font=dict(color=INK))
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
    st.caption("Several reviewers say Gold likes \"used to be unlimited\". "
               "A lead to check against product changes around June 2026, not a confirmed cause.")

# ---------------------------------------------------------------- 3. incidents
st.subheader("3. The worst weeks were incidents, mostly releases")
st.caption("Complaints per week. Red weeks ran more than 2 standard deviations above the previous 8 weeks "
           "(the spike detector found them without being told where to look).")
fig = go.Figure()
fig.add_bar(x=wk["week_start"], y=wk["complaints"],
            marker=dict(color=[RED if sp else GREY for sp in wk["is_spike"]], cornerradius=3),
            customdata=wk["times_baseline"],
            hovertemplate="Week of %{x|%d %b %Y}: %{y} complaints (%{customdata}x normal)<extra></extra>")
fig.add_scatter(x=wk["week_start"], y=wk["baseline"], mode="lines", line=dict(color=INK_2, width=2, dash="dot"),
                hovertemplate="Normal level: %{y:.0f}<extra></extra>")
for _, r in wk[wk["is_spike"]].iterrows():
    label = f"{r['times_baseline']:.1f}x"
    if r["week_start"] == pd.Timestamp("2026-05-25"):
        label += " login outage"
    fig.add_annotation(x=r["week_start"], y=r["complaints"], text=label, showarrow=False, yshift=12,
                       font=dict(color=INK, size=12))
style(fig, height=340, y_title="Complaints")
st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
st.caption("Dotted line: the average of the previous 8 weeks.")

st.caption("Change in average rating for each app release compared with the release before it "
           "(Android versions with 30+ reviews)")
vv = versions[(versions["first_seen"] >= s) & (versions["first_seen"] <= e + pd.offsets.MonthEnd(1))].dropna(subset=["rating_change"])
fig = go.Figure(go.Bar(
    x=vv["app_version"], y=vv["rating_change"],
    marker=dict(color=[RED if c <= -0.5 else GREY for c in vv["rating_change"]], cornerradius=3),
    customdata=vv[["first_seen", "avg_rating"]],
    hovertemplate="%{x} (from %{customdata[0]|%d %b %Y}): %{y:+.2f} stars, avg %{customdata[1]:.2f}<extra></extra>"))
for _, r in vv[vv["rating_change"] <= -0.5].iterrows():
    fig.add_annotation(x=r["app_version"], y=r["rating_change"], text=f"{r['app_version']}<br>{r['rating_change']:+.2f}",
                       showarrow=False, yshift=-22, font=dict(color=INK, size=12))
style(fig, height=320, y_title="Stars vs previous release")
fig.update_xaxes(showticklabels=False, title="App releases, oldest to newest")
fig.update_yaxes(zeroline=True, zerolinecolor="#b8b6ae")
st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)

# ---------------------------------------------------------------- 4. trend
st.subheader("4. Monthly complaint rate")
st.caption("Share of reviews that are 1-2 stars. Reviewers are polarised: "
           f"{headline['pct_5_star']:.0%} give 5 stars and {headline['pct_1_star']:.0%} give 1 star, "
           "so reviews show what hurts, not how many members it hurts.")
rate = m["complaints"] / m["reviews"]
fig = go.Figure(go.Scatter(x=m["month"], y=rate, mode="lines+markers", line=dict(color=BLUE, width=2),
                           marker=dict(size=8, color=BLUE, line=dict(color="white", width=2)),
                           hovertemplate="%{x|%b %Y}: %{y:.0%} complaints<extra></extra>"))
style(fig, height=300, pct=True)
st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)

# ---------------------------------------------------------------- method + data
with st.expander("Method and limitations"):
    st.markdown("""
- **Data:** the newest 5,000 English Google Play reviews. Google returned the same reviews for every country,
  so there is no market split, and Apple's public feed returned too few reviews to use.
- **Complaint** = a 1-2 star review. Star ratings were more reliable than text sentiment (VADER),
  which scored complaints like "app crashes after the update" as neutral.
- **Journey stages and Gold reasons** come from keyword rules. They cover 76% of complaints, so they are a
  first pass, not a trained classifier. English only.
- **Analysis layer:** the same logic runs as SQL views in BigQuery (see `sql/` on GitHub);
  this dashboard reads an aggregated snapshot so it stays online.
- **Next step with Muzz's own data:** confirm the Gold finding in Mixpanel and test a fix
  (see `TRACKING_PLAN.md`).
""")
with st.expander("See the data behind the charts"):
    tab1, tab2, tab3 = st.tabs(["Monthly", "Spike weeks", "Releases"])
    tab1.dataframe(m.assign(avg_rating=m["rating_sum"] / m["reviews"], complaint_rate=rate)
                   .drop(columns="rating_sum"), hide_index=True, use_container_width=True)
    tab2.dataframe(weekly[weekly["is_spike"]][["week_start", "reviews", "complaints", "baseline", "times_baseline"]],
                   hide_index=True, use_container_width=True)
    tab3.dataframe(versions, hide_index=True, use_container_width=True)
