# From reviews to product data: tracking plan and test

Reviews tell you *what members say*. Product data tells you *what members do*. This page shows how I'd check the reviews' biggest finding in Mixpanel, then fix it with an A/B test.

> The reviews' biggest finding: **42% of complaints mention Gold**, and the fastest-growing reason is **paying members still hitting limits on likes** (below 1 per 100 reviews for 12 months, then 7 per 100 in July 2026). Below is how I'd check that in Mixpanel and test a fix.

## 1. Member journey events (Mixpanel tracking plan)

| Stage | Event | Fires when | Key properties |
| --- | --- | --- | --- |
| Sign-up | `signup_started` | First sign-up screen viewed | `platform`, `country`, `acquisition_source`, `app_version` |
| Sign-up | `signup_completed` | Phone number confirmed by SMS | `platform`, `country`, `seconds_to_complete` |
| Verification | `selfie_submitted` | Member submits a verification selfie | `attempt_number` |
| Verification | `selfie_result` | Verification decision returned | `result` (approved / rejected / manual_review), `rejection_reason`, `seconds_to_decision` |
| Profile | `profile_completed` | Required profile fields saved | `photos_count`, `has_intro_video`, `photos_hidden` |
| Matching | `like_sent` / `match_created` | Member likes / a mutual match happens | `source` (discover, search), `filters_used` |
| Messaging | `message_sent` | Message sent in a match | `is_first_message`, `wali_present` |
| Messaging | `video_call_started` | In-app call begins | `duration_seconds` |
| Gold | `paywall_viewed` / `gold_purchased` | Paywall shown / subscription bought | `trigger`, `plan`, `price_local`, `currency` |
| Trust | `report_submitted` | Member reports a profile | `reason` |
| Success | `member_left_success` | Member leaves saying they met someone | `met_on_muzz` |

**Naming rules:** object then action, in `snake_case` and the past tense. Each event fires exactly once per action, and the same properties are always sent on every platform.

## 2. Check the review finding in Mixpanel

1. **Did something change?** Check the release notes and Gold configuration for early June 2026 first. The reviews point to a change in Gold's likes allowance, and the product data should confirm it before anything else.
2. **Funnel report for Gold members:** `gold_purchased` to `daily_like_limit_reached` to `paywall_viewed (extra likes)` to `gold_cancelled`. How many new Gold members hit the limit in their first week, and how does that compare with before June?
3. **Retention by cohort:** Gold renewal rate and refund requests for members who subscribed before vs after the change.
4. **Break it down** by `country`, `platform` and gender of the member. Reviews suggest men hit paywalls more, so check whether that holds.
5. **Size it:** members who hit the limit each month, multiplied by the drop in renewal rate and the Gold price. That gives the revenue at stake, to weigh against any revenue from selling extra likes.

Extra event this needs: `daily_like_limit_reached` (`plan`, `likes_used`, `limit`).

## 3. A/B test to fix it

| | |
| --- | --- |
| **Hypothesis** | Showing Gold members their remaining likes clearly, and telling them about the limit before they buy, will reduce "I paid and I'm still limited" frustration without hurting revenue. |
| **Unit** | Member, randomised at `paywall_viewed` for new Gold buyers |
| **Primary metric** | Gold renewal rate at the end of the first billing period |
| **Guardrails** | Gold conversion at the paywall (it mustn't fall much), refund requests, 1-2 star review rate, extra-likes revenue |
| **Sample size** | Planned in advance for the smallest uplift in renewal worth shipping, at 80% power. My [Holdout planner](https://holdout-ab.streamlit.app) does this. |
| **Duration** | At least one full billing cycle, in whole weeks. No stopping early because it looks good, because daily checking raises false positives from 4% to 24%. |
| **Checks** | Sample ratio mismatch, balance across country, platform and plan length |
| **Decision rule** | Ship if renewal improves and conversion and revenue guardrails hold. Then look at results by market before rolling out everywhere. |
