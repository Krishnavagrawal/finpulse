"""
2. INSIGHT AGENT
------------------
Consumes raw events from the Observer Agent and turns them into structured
"insights": trend detection, anomaly detection, opportunity identification,
plus NLP-generated copy via the ML/NLP service.
"""
from services import cache
from services import ml_service


def run(user_id, events):
    insights = []
    for e in events:
        if e["type"] == "idle_cash":
            insights.append(_idle_cash_insight(e))
        elif e["type"] == "upcoming_schedule" and e["covered"]:
            insights.append(_upcoming_schedule_insight(e))
        elif e["type"] == "upcoming_schedule" and not e["covered"]:
            insights.append(_low_balance_insight(e))
        elif e["type"] == "spending_spike":
            insights.append(_spending_spike_insight(e))
        elif e["type"] == "paused_sip":
            insights.append(_paused_sip_insight(e))

    cache.log_pipeline_step(user_id, "Insight Agent", {
        "events_analyzed": len(events),
        "insights_generated": len(insights),
        "categories": [i["category"] for i in insights],
    })
    return insights


def _idle_cash_insight(e):
    context = {"amount": e["amount"], "days": e["days_idle"]}
    return {
        "category": "idle_cash",
        "opportunity_type": "investment_opportunity",
        "context": context,
        "message": ml_service.generate_nudge_copy("idle_cash", context),
        "raw_event": e,
        "base_relevance": 0.9,
        "base_urgency": 0.4,
    }


def _upcoming_schedule_insight(e):
    context = {"label": e["label"], "amount": e["amount"], "days": e["days_left"], "due_date": e["due_date"]}
    return {
        "category": "upcoming_emi" if e["schedule_type"] == "EMI" else "upcoming_bill",
        "opportunity_type": "reminder",
        "context": context,
        "message": ml_service.generate_nudge_copy("upcoming_emi", context),
        "raw_event": e,
        "base_relevance": 0.6,
        "base_urgency": 0.5 + (0.5 * (7 - e["days_left"]) / 7),
    }


def _low_balance_insight(e):
    context = {"label": e["label"], "amount": e["amount"], "due_date": e["due_date"]}
    return {
        "category": "low_balance_warning",
        "opportunity_type": "risk_alert",
        "context": context,
        "message": ml_service.generate_nudge_copy("low_balance_warning", context),
        "raw_event": e,
        "base_relevance": 0.95,
        "base_urgency": 0.9,
    }


def _spending_spike_insight(e):
    context = {"merchant_category": e["category"], "pct": e["pct_increase"]}
    return {
        "category": "spending_spike",
        "opportunity_type": "anomaly",
        "context": context,
        "message": ml_service.generate_nudge_copy("spending_spike", context),
        "raw_event": e,
        "base_relevance": 0.5,
        "base_urgency": 0.2,
    }


def _paused_sip_insight(e):
    context = {"label": e["label"], "amount": e["amount"]}
    return {
        "category": "paused_sip",
        "opportunity_type": "investment_opportunity",
        "context": context,
        "message": ml_service.generate_nudge_copy("paused_sip", context),
        "raw_event": e,
        "base_relevance": 0.75,
        "base_urgency": 0.3,
    }
