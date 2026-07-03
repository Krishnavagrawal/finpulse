"""
ML / NLP Service
-----------------
Stands in for the "LLM / Fine-tuned Model" block. For the hackathon
prototype this is a deterministic, template-driven generator so the demo
is reliable and needs no API key. The interface (`generate_nudge_copy`,
`classify_intent`) is written so it's a drop-in swap for a real LLM call
(e.g. the Claude API) later — see README for how to wire that up.
"""

TEMPLATES = {
    "idle_cash": [
        "₹{amount:,.0f} has been sitting idle in your account for {days} days. "
        "Move it into a Liquid Fund and earn up to 6.5% p.a. instead of ~3% in savings.",
        "You're carrying an unusually high idle balance of ₹{amount:,.0f}. "
        "A quick sweep into a Liquid Fund keeps it accessible and earning more.",
    ],
    "upcoming_emi": [
        "Your {label} of ₹{amount:,.0f} is due in {days} days. "
        "Your available balance covers it, but here's a quick reminder so you don't miss it.",
        "Heads up — {label} (₹{amount:,.0f}) is due on {due_date}. Want to set it on auto-pay?",
    ],
    "low_balance_warning": [
        "Your available balance may fall short of the {label} due on {due_date}. "
        "Consider moving funds from your savings account before then.",
    ],
    "spending_spike": [
        "Your spending on {merchant_category} this month is {pct}% higher than your usual average. "
        "Just flagging it — no action needed unless you want to review.",
    ],
    "paused_sip": [
        "Your {label} has been paused for a while. Resuming it now keeps your goal on track — "
        "restarting a ₹{amount:,.0f} SIP today still gives it years to compound.",
    ],
    "goal_progress": [
        "Nice pace — at this rate you'll hit your savings goal roughly {days} days sooner than planned.",
    ],
}


def generate_nudge_copy(category, context, variant=0):
    """Fill a template with live context. `variant` lets the Decision Agent
    A/B different phrasings for the same nudge category."""
    options = TEMPLATES.get(category, ["We noticed something worth your attention."])
    template = options[variant % len(options)]
    try:
        return template.format(**context)
    except (KeyError, IndexError):
        return template


def classify_intent(user_message: str) -> str:
    """Very small keyword-based intent classifier standing in for an
    NLP intent-classification model, used if the user replies to a nudge
    with free text (not exercised by the default UI, but wired for
    future chat-based interaction with FinPulse)."""
    text = user_message.lower()
    if any(w in text for w in ["invest", "sip", "mutual fund"]):
        return "investment_intent"
    if any(w in text for w in ["pay", "bill", "due"]):
        return "payment_intent"
    if any(w in text for w in ["stop", "no", "not now", "later"]):
        return "dismiss_intent"
    return "unknown"
