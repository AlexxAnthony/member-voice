"""
Step 2 - Add sentiment and member-journey tags.

For every review this adds:
- sentiment (VADER compound score, -1 to +1) and a label (positive / neutral / negative)
- journey stages it mentions, in the order a member moves through the app:
    1 sign-up -> 2 verification -> 3 profile -> 4 matching -> 5 messaging
    -> 6 Gold / payment, plus cross-cutting themes: trust & safety, app quality,
    customer support. Reviews written mainly in Arabic or Hindi/Urdu script are
    marked x_non_english, because the English rules can't read them.
- gold_issue: for reviews about Gold, the reason (billing, limits for paying
  members, basics behind the paywall, no results, price).
  A review can mention several stages, so they are stored pipe-separated
  ("verification|matching") and unnested in BigQuery.
- is_complaint: rating of 2 stars or fewer (the main "unhappy" signal - see below)
- success_story: the review says the member met their partner / got married.

Limitation: VADER and the keyword rules are English-only, and keyword tagging
is a first pass, not a trained classifier. Both are stated in the README.

Run:  python enrich.py
In:   data/raw_reviews.csv
Out:  data/reviews_enriched.csv
"""
import re
from pathlib import Path

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

IN = Path("data/raw_reviews.csv")
OUT = Path("data/reviews_enriched.csv")

# Ordered as the member journey. Keywords are matched as whole words/phrases.
STAGES = {
    "1_sign_up": ["sign up", "signup", "sign-up", "register", "registration", "onboarding",
                  "create an account", "create account", "creat acount", "otp", "sms code",
                  "verification code", "phone number", "log in", "login", "logged out", "log out",
                  "logout", "logs me out", "log you out", "can't log", "cannot log", "account"],
    "2_verification": ["selfie", "verify", "verified", "verification", "verifying",
                       "under review", "pending approval", "rejected", "approval"],
    "3_profile": ["profile", "bio", "photos", "photo", "pictures", "picture", "prompts",
                  "nickname", "intro video", "voice intro"],
    "4_matching": ["match", "matches", "matching", "matched", "swipe", "swiping", "likes",
                   "algorithm", "filter", "filters", "distance", "same people",
                   "same profiles", "no one", "nobody", "few people", "location", "results",
                   "serious", "time pass", "timepass", "time waster", "time wasters",
                   "wasting time", "waste of time", "ghost", "ghosted", "ghosting", "visits"],
    "5_messaging": ["message", "messages", "messaging", "chat", "chats", "chatting", "reply",
                    "replies", "conversation", "wali", "chaperone", "video call", "calling", "text"],
    "6_gold_payment": ["gold", "premium", "subscription", "subscribe", "subscribed", "pay", "paid",
                       "paying", "payment", "payments", "price", "pricing", "expensive", "money",
                       "refund", "charged", "boost", "boosts", "instant chat", "cost", "costs",
                       "costly", "cheap", "worth", "plan", "deduct", "deducted", "deducting",
                       "billing", "cancel", "cancelled", "cancellation", "paywall", "blurred",
                       "blur", "compliment", "compliments"],
    "x_trust_safety": ["fake", "scam", "scammer", "scammers", "catfish", "bot", "bots", "spam",
                       "harass", "harassment", "inappropriate", "banned", "ban", "suspended",
                       "safety", "safe", "already married", "creepy", "privacy", "data",
                       "porn", "non muslim", "non muslims", "non-muslim", "non-muslims"],
    "x_app_quality": ["crash", "crashes", "crashing", "bug", "bugs", "buggy", "glitch",
                      "glitches", "slow", "loading", "freeze", "freezes", "not working",
                      "doesn't work", "error", "update", "something went wrong", "retry",
                      "try again later"],
    "x_support": ["support", "customer service", "customer care", "help team", "helpdesk",
                  "no response", "no reply from", "contact", "email", "emailed"],
}
# Reviews mostly in Arabic or Devanagari script can't be read by the English rules.
NON_ENGLISH_RX = re.compile(r"[\u0600-\u06FF\u0900-\u097F]")

# Why are members unhappy about Gold? First matching reason wins (order matters).
GOLD_ISSUES = {
    "Billing, refunds & cancellation": ["refund", "charged", "deduct", "deducted", "deducting",
                                        "cancel", "cancelled", "cancellation", "billing", "renew",
                                        "renewed", "auto renew", "took money", "taken money"],
    "Paid but still limited": ["limit", "limits", "limited", "boost", "boosts", "compliment",
                               "compliments", "1hr", "1 hour", "24hr", "24 hours", "even after paying",
                               "even with gold", "paying members", "paid members", "more likes", "extra likes",
                               "buy more", "cap", "unlimited", "restricted", "20 likes"],
    "Basics behind the paywall": ["who liked", "see who", "blur", "blurred", "can't message",
                                  "can't text", "cannot message", "forcefully", "have to pay",
                                  "need to pay", "must pay", "everything costs", "paywall", "if you don't pay",
                                  "if you dont pay", "pay to match", "must be gold", "monetized",
                                  "monetised", "have to buy", "popup", "popups", "pop up",
                                  "push you to buy"],
    "Paid but no results": ["no matches", "zero matches", "no match", "waste of money",
                            "wasted my money", "not worth", "no results", "nobody", "no one",
                            "still single", "not showing", "not shown", "unseen"],
    "Price": ["expensive", "price", "pricing", "costly", "cheap", "overpriced"],
    "Feels like a money grab": ["money grab", "money grabbing", "money making", "money maker",
                                "greedy", "greed", "squeeze", "predatory", "just want money",
                                "steal", "take your money", "takes your money", "cut my money",
                                "scam", "fraud", "frud"],
}
SUCCESS = ["got married", "married my", "met my husband", "met my wife", "found my husband",
           "found my wife", "found my partner", "met my partner", "nikah", "engaged",
           "found the one", "my spouse", "success story"]


def _compile(words):
    return re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.I)


STAGE_RX = {k: _compile(v) for k, v in STAGES.items()}
SUCCESS_RX = _compile(SUCCESS)
GOLD_RX = {k: _compile(v) for k, v in GOLD_ISSUES.items()}


def tag_stages(text: str) -> str:
    tags = [k for k, rx in STAGE_RX.items() if rx.search(text)]
    if not tags and len(NON_ENGLISH_RX.findall(text)) > len(text) * 0.3:
        tags = ["x_non_english"]
    return "|".join(tags) or "untagged"


def gold_issue(text: str, stages: str) -> str:
    if "6_gold_payment" not in stages:
        return ""
    for k, rx in GOLD_RX.items():
        if rx.search(text):
            return k
    return "Other Gold mention"


if __name__ == "__main__":
    df = pd.read_csv(IN, dtype={"app_version": str})
    df["text"] = (df["title"].fillna("") + ". " + df["content"].fillna("")).str.strip(". ").str.strip()
    df = df[df["text"].str.len() > 0].copy()

    sia = SentimentIntensityAnalyzer()
    df["sentiment"] = df["text"].map(lambda t: round(sia.polarity_scores(t)["compound"], 4))
    df["sentiment_label"] = pd.cut(df["sentiment"], [-1.01, -0.05, 0.05, 1.01],
                                   labels=["negative", "neutral", "positive"]).astype(str)
    # Star rating is the more reliable "unhappy" signal: VADER under-scores
    # complaint language (e.g. "app crashes after the update" scores neutral).
    df["is_complaint"] = df["rating"] <= 2
    df["stages"] = df["text"].map(tag_stages)
    df["gold_issue"] = [gold_issue(t, st) for t, st in zip(df["text"], df["stages"])]
    df["success_story"] = df["text"].map(lambda t: bool(SUCCESS_RX.search(t)))
    df["word_count"] = df["text"].str.split().str.len()

    cols = ["review_id", "platform", "market", "review_date", "rating", "sentiment",
            "sentiment_label", "is_complaint", "stages", "gold_issue", "success_story", "app_version", "thumbs_up",
            "developer_replied", "reply_date", "word_count", "text"]
    df[cols].to_csv(OUT, index=False)

    print(f"Saved {len(df):,} reviews to {OUT}")
    print(f"Tagged with at least one journey stage: {(df['stages'] != 'untagged').mean():.0%}")
    print(f"Complaints tagged: {(df.loc[df['is_complaint'], 'stages'] != 'untagged').mean():.0%}")
    print(f"Complaints (rating <= 2): {df['is_complaint'].mean():.0%}")
    # Sanity check: how often does VADER agree with the star rating?
    low, high = df[df["rating"] <= 2], df[df["rating"] >= 4]
    print(f"VADER calls 1-2 star reviews negative: {(low['sentiment_label'] == 'negative').mean():.0%}")
    print(f"VADER calls 4-5 star reviews positive: {(high['sentiment_label'] == 'positive').mean():.0%}")
