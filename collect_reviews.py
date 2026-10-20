"""
Step 1 - Collect public Muzz app reviews.

Sources
- Apple App Store: public RSS feed, one feed per country storefront, so the
  `market` column is a real market. Apple exposes up to ~500 most recent
  reviews per country.
- Google Play: the newest English reviews, pulled per market. The script checks
  whether Google really returns different reviews per market; if not, the
  Android rows are labelled market = "GLOBAL".
- Apple's public RSS feed is limited and sometimes returns very little, so the
  App Store is a small extra source, not the main one.

Privacy
- Reviewer names, avatars and profile links are never stored.
- Review IDs are hashed, so rows cannot be traced back to a person.

Run:  python collect_reviews.py
Out:  data/raw_reviews.csv
"""
import hashlib
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

# Markets to pull from the App Store (ISO country codes).
APP_STORE_MARKETS = ["gb", "us", "ca", "au", "in", "ae", "sa", "pk", "my", "sg",
                     "id", "fr", "de", "nl", "za", "ng", "eg", "qa", "kw", "bh"]
SEARCH_TERM = "Muzz"

OUT = Path("data/raw_reviews.csv")


def _hash(x) -> str:
    return hashlib.sha256(str(x).encode()).hexdigest()[:16]


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def find_app_store_id() -> int:
    data = _get_json(f"https://itunes.apple.com/search?term={SEARCH_TERM}&entity=software&country=gb&limit=10")
    for item in data.get("results", []):
        if item.get("trackName", "").lower().startswith("muzz"):
            print(f"App Store app: {item['trackName']} (id {item['trackId']})")
            return item["trackId"]
    raise SystemExit("Could not find Muzz on the App Store - set the id manually.")


def collect_app_store(app_id: int) -> list[dict]:
    rows = []
    for cc in APP_STORE_MARKETS:
        n = 0
        for page in range(1, 11):
            url = f"https://itunes.apple.com/{cc}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
            try:
                entries = _get_json(url).get("feed", {}).get("entry", [])
            except Exception as e:
                print(f"  {cc} page {page}: {e}")
                break
            if isinstance(entries, dict):
                entries = [entries]
            entries = [e for e in entries if "im:rating" in e]  # first entry can be app metadata
            if not entries:
                break
            for e in entries:
                rows.append({
                    "review_id": _hash("ios" + e["id"]["label"]),
                    "platform": "iOS",
                    "market": cc.upper(),
                    "review_date": e["updated"]["label"][:10],
                    "rating": int(e["im:rating"]["label"]),
                    "title": e.get("title", {}).get("label", ""),
                    "content": e.get("content", {}).get("label", ""),
                    "app_version": e.get("im:version", {}).get("label", ""),
                    "thumbs_up": None,
                    "developer_replied": None,
                    "reply_date": None,
                })
                n += 1
            time.sleep(0.5)
        print(f"  App Store {cc.upper()}: {n} reviews")
    return rows


KNOWN_PLAY_ID = "com.muzmatch.muzmatchapp"   # Muzz's Google Play package (fallback)
PLAY_MARKETS = ["gb", "in", "ae"]              # checked for overlap; Google returns the same reviews
PLAY_PER_MARKET = 5000                       # enough to get every English written review


def find_play_id() -> str:
    """Search Google Play; fall back to the known package id if search returns a blank id."""
    from google_play_scraper import app, search
    candidates = [r.get("appId") for r in search(SEARCH_TERM, lang="en", country="gb", n_hits=10)
                  if r.get("appId") and r.get("title", "").lower().startswith("muzz")]
    for app_id in candidates + [KNOWN_PLAY_ID]:
        try:
            info = app(app_id, lang="en", country="gb")
            print(f"Google Play app: {info['title']} ({app_id}) - {info.get('reviews', 0):,} written reviews, "
                  f"rating {info.get('score', 0):.2f}")
            return app_id
        except Exception as e:
            print(f"  {app_id}: {e}")
    raise SystemExit("Could not find Muzz on Google Play - open its Play Store page and copy the id= value into KNOWN_PLAY_ID.")


def collect_google_play(app_id: str) -> list[dict]:
    """Pull the newest English reviews for each market separately, then check
    whether Google actually returns different reviews per market."""
    from google_play_scraper import Sort, reviews
    rows = []
    for cc in PLAY_MARKETS:
        token, n = None, 0
        while n < PLAY_PER_MARKET:
            try:
                batch, token = reviews(app_id, lang="en", country=cc, sort=Sort.NEWEST,
                                       count=min(200, PLAY_PER_MARKET - n), continuation_token=token)
            except Exception as e:
                print(f"  Google Play {cc.upper()}: stopped ({e})")
                break
            if not batch:
                break
            for r in batch:
                rows.append({
                    "raw_id": r["reviewId"],
                    "review_id": _hash("android" + r["reviewId"]),
                    "platform": "Android",
                    "market": cc.upper(),
                    "review_date": r["at"].date().isoformat(),
                    "rating": int(r["score"]),
                    "title": "",
                    "content": r.get("content") or "",
                    "app_version": r.get("reviewCreatedVersion") or "",
                    "thumbs_up": r.get("thumbsUpCount", 0),
                    "developer_replied": r.get("replyContent") is not None,
                    "reply_date": r["repliedAt"].date().isoformat() if r.get("repliedAt") else None,
                })
            n += len(batch)
            if token is None:
                break
            time.sleep(0.5)
        print(f"  Google Play {cc.upper()}: {n} reviews")

    if not rows:
        return rows
    df = pd.DataFrame(rows)
    seen_in = df.groupby("raw_id")["market"].nunique()
    overlap = (seen_in > 1).mean()
    print(f"  Google Play reviews returned for more than one market: {overlap:.0%}")
    if overlap > 0.2:
        print("  -> Google is not separating reviews by market, so Android reviews are labelled GLOBAL.")
        df["market"] = "GLOBAL"
    else:
        print("  -> Markets look genuinely separate, so the Android market labels are kept.")
    df = df.drop_duplicates("raw_id").drop(columns="raw_id")
    return df.to_dict("records")


if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    rows = collect_app_store(find_app_store_id()) + collect_google_play(find_play_id())
    df = pd.DataFrame(rows).drop_duplicates("review_id")
    df.to_csv(OUT, index=False)
    print(f"\nSaved {len(df):,} reviews to {OUT}")
    print(df.groupby(["platform", "market"]).agg(reviews=("rating", "size"),
                                                 from_date=("review_date", "min"),
                                                 to_date=("review_date", "max")).to_string())
