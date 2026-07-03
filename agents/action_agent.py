"""
4. ACTION AGENT
------------------
Two jobs, matching the two arrows leaving this box in the architecture
diagram:
 1. prepare(): package each surfaced Decision-Agent output into a nudge
    (title/message/channel/action) and persist it, then "deliver" it via
    the User Engagement layer (push / in-app / email-sms).
 2. execute(): when the user taps the one-tap action on a nudge (Invest
    Now, Pay Bill, Start SIP...), actually call the External Services
    layer and record the outcome.
"""
from services import database as db
from services import cache
from services import external_services as ext

TITLES = {
    "idle_cash": "Idle cash spotted",
    "paused_sip": "Your SIP is paused",
    "upcoming_emi": "EMI coming up",
    "upcoming_bill": "Bill due soon",
    "low_balance_warning": "Balance may fall short",
    "spending_spike": "Spending is up this month",
}


def prepare(user_id, decisions):
    delivered = []
    for d in decisions:
        if d["decision"] != "surface":
            continue
        nudge = {
            "user_id": user_id,
            "agent_source": "action_agent",
            "category": d["category"],
            "title": TITLES.get(d["category"], "FinPulse Insight"),
            "message": d["message"],
            "relevance_score": d["relevance_score"],
            "urgency_score": d["urgency_score"],
            "final_score": d["final_score"],
            "channel": d["channel"],
            "action_type": d["action_type"],
            "action_payload": _build_payload(d),
        }
        nudge_id = db.insert_nudge(nudge)
        nudge["id"] = nudge_id

        if "push" in d["channel"]:
            ext.send_push_notification(user_id, nudge["title"], nudge["message"])
        delivered.append(nudge)

    cache.log_pipeline_step(user_id, "Action Agent", {
        "nudges_delivered": len(delivered),
        "channels_used": list({n["channel"] for n in delivered}),
    })
    return delivered


def _build_payload(decision):
    ctx = decision.get("context", {})
    amount = ctx.get("amount", 0)
    label = ctx.get("label", "")
    return f"{decision['action_type']}|{amount}|{label}"


def execute(nudge_id):
    """Called when the user taps the action button on a nudge."""
    nudge = db.get_nudge(nudge_id)
    if not nudge:
        return {"status": "error", "message": "Nudge not found"}

    action_type, amount_str, label = (nudge["action_payload"].split("|") + ["0", ""])[:3]
    amount = float(amount_str) if amount_str else 0.0

    if action_type == "invest":
        result = ext.invest_in_liquid_fund(nudge["user_id"], amount)
    elif action_type == "pay_bill":
        result = ext.pay_bill(nudge["user_id"], label or "Biller", amount)
    elif action_type == "start_sip":
        result = ext.start_sip(nudge["user_id"], label or "SIP", amount)
    else:
        result = {"status": "acknowledged"}

    db.update_nudge_status(nudge_id, "actioned")
    db.record_feedback(nudge_id, nudge["user_id"], nudge["category"], "accepted")
    db.adjust_category_weight(nudge["user_id"], nudge["category"], +0.15)

    cache.log_pipeline_step(nudge["user_id"], "Action Agent (execute)", {
        "nudge_id": nudge_id, "action_type": action_type, "result": result["status"],
    })
    return {"status": "success", "result": result}
