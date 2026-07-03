"""
1. OBSERVER AGENT
------------------
Monitors financial events in real-time: transactions, balances, schedules,
and user behavior. Emits raw "events" that the Insight Agent will interpret.
In production this would subscribe to a Kafka/Redis Streams feed off the
Ingestion Layer; here it polls the operational DB directly for the demo.
"""
from datetime import datetime
from services import database as db
from services import cache


AVG_SAVINGS_RATE = 0.03      # typical SBI savings account rate
LIQUID_FUND_RATE = 0.065     # typical liquid fund return
IDLE_CASH_THRESHOLD = 10000  # flag idle balances above this
IDLE_DAYS_THRESHOLD = 30     # ...if no investment activity in this many days


def run(user_id):
    """Scans a user's accounts, transactions and schedules and returns a
    list of raw events for the Insight Agent to analyze."""
    events = []
    accounts = db.get_accounts(user_id)
    txns = db.get_transactions(user_id, limit=200)
    schedules = db.get_schedules(user_id)

    events.extend(_check_idle_cash(accounts, txns))
    events.extend(_check_upcoming_schedules(accounts, schedules))
    events.extend(_check_spending_pattern(txns))
    events.extend(_check_paused_sip(schedules))

    for e in events:
        cache.publish_event(user_id, e)

    cache.log_pipeline_step(user_id, "Observer Agent", {
        "accounts_scanned": len(accounts),
        "transactions_scanned": len(txns),
        "schedules_scanned": len(schedules),
        "events_emitted": len(events),
        "event_types": [e["type"] for e in events],
    })
    return events


def _check_idle_cash(accounts, txns):
    events = []
    invested_recently = any(t["category"] == "investment" for t in txns)
    for acc in accounts:
        if acc["account_type"] == "savings" and acc["balance_available"] >= IDLE_CASH_THRESHOLD:
            if not invested_recently:
                events.append({
                    "type": "idle_cash",
                    "account_id": acc["id"],
                    "amount": acc["balance_available"],
                    "days_idle": IDLE_DAYS_THRESHOLD + 15,  # demo value
                })
    return events


def _check_upcoming_schedules(accounts, schedules):
    events = []
    total_available = sum(a["balance_available"] for a in accounts if a["account_type"] in ("savings", "current"))
    today = datetime.now()
    for s in schedules:
        if s["status"] != "upcoming":
            continue
        due = datetime.strptime(s["due_date"], "%Y-%m-%d")
        days = (due - today).days
        if 0 <= days <= 7:
            events.append({
                "type": "upcoming_schedule",
                "schedule_id": s["id"],
                "schedule_type": s["schedule_type"],
                "label": s["label"],
                "amount": s["amount"],
                "due_date": s["due_date"],
                "days_left": days,
                "covered": total_available >= s["amount"],
            })
    return events


def _check_spending_pattern(txns):
    events = []
    debits = [t for t in txns if t["direction"] == "debit"]
    if len(debits) < 6:
        return events
    recent = debits[:8]
    older = debits[8:16] or debits[:8]
    recent_avg = sum(t["amount"] for t in recent) / max(1, len(recent))
    older_avg = sum(t["amount"] for t in older) / max(1, len(older))
    if older_avg > 0 and recent_avg > older_avg * 1.35:
        pct = round((recent_avg - older_avg) / older_avg * 100)
        top_cat = max(set(t["category"] for t in recent), key=lambda c: sum(1 for t in recent if t["category"] == c))
        events.append({
            "type": "spending_spike",
            "category": top_cat,
            "pct_increase": pct,
        })
    return events


def _check_paused_sip(schedules):
    events = []
    for s in schedules:
        if s["schedule_type"] == "SIP" and s["status"] == "paused":
            events.append({
                "type": "paused_sip",
                "schedule_id": s["id"],
                "label": s["label"],
                "amount": s["amount"],
            })
    return events
