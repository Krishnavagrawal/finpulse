# FinPulse — Proactive Financial Wellness Agent for SBI YONO

A multi-agent system that watches a customer's YONO accounts and proactively
nudges them toward better financial decisions — idle cash into a liquid
fund, a heads-up before an EMI is due, a nudge to resume a paused SIP —
instead of waiting for the customer to go looking.

This repo is a runnable prototype of the four-agent architecture: every
box in the architecture diagram has real, working code behind it.

## Architecture → Code map

| Diagram block | Code |
|---|---|
| Ingestion Layer / Kafka / Redis Streams | `services/cache.py` (`publish_event`) |
| 1. Observer Agent | `agents/observer_agent.py` |
| 2. Insight Agent | `agents/insight_agent.py` |
| 3. Decision Agent | `agents/decision_agent.py` |
| 4. Action Agent | `agents/action_agent.py` |
| Operational Database (PostgreSQL) | `services/database.py` (SQLite for the prototype) |
| Cache / Queue (Redis) | `services/cache.py` |
| ML / NLP Service | `services/ml_service.py` |
| External Services (SBI APIs / Partners) | `services/external_services.py` |
| Feedback Loop | `services/feedback_loop.py` |
| User Engagement (Push / In-app / Email) | `services/external_services.py` + nudge feed in `templates/index.html` |
| Security & Compliance | `users.kyc_verified` / `consent_given` fields in the schema — see "Next steps" below for what a production build adds |

## How the pipeline runs

`POST /api/run-pipeline/<user_id>` does, in order:

1. **Observer Agent** scans accounts, transactions and schedules for raw
   events: idle cash, upcoming EMIs/bills, spending spikes, paused SIPs.
2. **Insight Agent** turns each event into an insight with NLP-generated
   copy (template-driven in the prototype — see "Swapping in a real LLM").
3. **Decision Agent** scores each insight on relevance and urgency, applies
   a daily frequency cap (max 3 nudges/day) and a suppression threshold, and
   picks a channel.
4. **Action Agent** persists the surfaced nudges and "delivers" them (push
   notification simulated); when the user taps a nudge's action button, the
   same agent executes it against the mock External Services layer
   (`invest_in_liquid_fund`, `pay_bill`, `start_sip`).
5. **Feedback Loop** records accept/dismiss and adjusts a per-user,
   per-category relevance weight up or down — so the Decision Agent scores
   that category differently next run. This is a lightweight stand-in for
   "Model Re-training & Optimization" that you can see change live in a demo.

The right-hand "Multi-Agent Pipeline" panel in the UI plays back the trace
of what each agent did, node by node, so the hand-off between agents is
visible rather than just the final nudge.

## Running it locally

```bash
cd finpulse
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5000**. Click **Run Daily Scan** to trigger the
pipeline against the seeded demo user (idle savings balance, an EMI due in
3 days, a paused SIP). Tap a nudge's action button to execute it, or
Dismiss to see the feedback loop adjust the category's weight — run the
scan again and watch the mix of nudges shift.

**Reset Demo** wipes and re-seeds the database if you want to start over
mid-demo.

## Swapping in a real LLM

`services/ml_service.py` is written as a drop-in seam. Replace
`generate_nudge_copy()` with a call to the Claude API to generate copy
dynamically instead of from templates, e.g.:

```python
import anthropic
client = anthropic.Anthropic()

def generate_nudge_copy(category, context, variant=0):
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": f"Write a one-sentence, friendly nudge for a banking "
                       f"app. Category: {category}. Details: {context}."
        }]
    )
    return resp.content[0].text
```

Everything upstream (Observer/Insight event detection) and downstream
(Decision scoring, Action execution) is unchanged — only the copywriting
step changes.

## Next steps for a production build

- Swap SQLite → PostgreSQL and the in-process cache → Redis (interfaces in
  `services/database.py` and `services/cache.py` are already narrow enough
  to re-point at real connections without touching the agents).
- Replace the mock `services/external_services.py` calls with real SBI/YONO
  API integrations (mutual funds, billers, payments, KYC, credit bureau).
- Add OAuth2 + 2FA on the API layer, encrypt data in transit/at rest, and
  add audit logging — the Security & Compliance box in the architecture
  diagram is intentionally out of scope for a hackathon prototype but is
  the first thing to add before any real account data touches this code.
- Move the Observer Agent from polling the DB to actually subscribing to a
  Kafka/Redis Streams feed off the ingestion layer for true real-time
  detection instead of on-demand scans.

## Project structure

```
finpulse/
├── app.py                     # Flask app / REST API
├── agents/
│   ├── observer_agent.py
│   ├── insight_agent.py
│   ├── decision_agent.py
│   └── action_agent.py
├── services/
│   ├── database.py            # operational DB (SQLite)
│   ├── cache.py                # cache/queue + pipeline trace log
│   ├── ml_service.py          # NLP insight/nudge copy generation
│   ├── external_services.py   # mock SBI APIs / partners
│   └── feedback_loop.py
├── templates/index.html
├── static/css/style.css
├── static/js/app.js
└── requirements.txt
```

## Pushing to GitHub

```bash
cd finpulse
git init
git add .
git commit -m "FinPulse: proactive financial wellness agent prototype"
git branch -M main
git remote add origin https://github.com/<your-username>/finpulse.git
git push -u origin main
```

If the repo doesn't exist yet on GitHub, create it first (empty, no
README/license so it doesn't conflict with this one) at
`https://github.com/new`, then run the commands above.
