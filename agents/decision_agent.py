"""
3. DECISION AGENT
-------------------
Takes insights from the Insight Agent and decides whether they're worth
surfacing at all: relevance scoring, urgency scoring, frequency capping,
channel selection, and suppression of low-value nudges.
"""
from datetime import datetime, timedelta
from services import database as db
from services import cache

SUPPRESSION_THRESHOLD = 0.35
MAX_NUDGES_PER_DAY = 3
ACTION_MAP = {
    "idle_cash": ("invest", "Invest Now"),
    "paused_sip": ("start_sip", "Resume SIP"),
    "upcoming_emi": ("pay_bill", "Set Reminder"),
    "upcoming_bill": ("pay_bill", "Pay Now"),
    "low_balance_warning": ("review", "Move Funds"),
    "spending_spike": ("none", "Review Spending"),
}


def run(user_id, insights):
    decisions = []
    recent = db.get_recent_nudges(user_id, hours=24)
    todays_count = len(recent)

    # sort candidate insights by a first-pass score so frequency capping
    # keeps the highest-value ones if we're near the daily limit
    scored = [(_score(user_id, i), i) for i in insights]
    scored.sort(key=lambda x: x[0]["final_score"], reverse=True)

    slots_left = max(0, MAX_NUDGES_PER_DAY - todays_count)

    for score, insight in scored:
        if score["final_score"] < SUPPRESSION_THRESHOLD:
            decisions.append({**insight, **score, "decision": "suppressed",
                               "reason": "Below relevance/urgency threshold"})
            continue
        if slots_left <= 0:
            decisions.append({**insight, **score, "decision": "suppressed",
                               "reason": "Daily nudge frequency cap reached"})
            continue
        action_type, action_label = ACTION_MAP.get(insight["category"], ("none", "View"))
        channel = _select_channel(score["final_score"])
        decisions.append({
            **insight, **score,
            "decision": "surface",
            "channel": channel,
            "action_type": action_type,
            "action_label": action_label,
        })
        slots_left -= 1

    cache.log_pipeline_step(user_id, "Decision Agent", {
        "insights_scored": len(insights),
        "surfaced": sum(1 for d in decisions if d["decision"] == "surface"),
        "suppressed": sum(1 for d in decisions if d["decision"] == "suppressed"),
        "daily_cap": MAX_NUDGES_PER_DAY,
        "already_sent_today": todays_count,
    })
    return decisions


def _score(user_id, insight):
    weight = db.get_category_weight(user_id, insight["category"])
    relevance = min(1.0, insight["base_relevance"] * weight)
    urgency = min(1.0, insight["base_urgency"])
    # relevance carries slightly more weight than urgency for a "proactive
    # wellness" product (vs. a pure transactional-alerts product)
    final_score = round(0.6 * relevance + 0.4 * urgency, 3)
    return {"relevance_score": round(relevance, 3), "urgency_score": round(urgency, 3),
            "final_score": final_score}


def _select_channel(final_score):
    if final_score >= 0.75:
        return "in_app_and_push"
    if final_score >= 0.5:
        return "in_app"
    return "push"
