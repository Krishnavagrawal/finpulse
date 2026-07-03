"""
FinPulse — Proactive Financial Wellness Agent for SBI YONO
=============================================================
Flask prototype implementing the four-agent architecture:
Observer -> Insight -> Decision -> Action, backed by an operational
database, a cache/queue layer, a mock ML/NLP service, and mock external
services, with a feedback loop closing the system.

Run:  python app.py
Then open http://localhost:5000
"""
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

from services import database as db
from services import cache
from services import feedback_loop
from agents import observer_agent, insight_agent, decision_agent, action_agent

app = Flask(__name__)
CORS(app)

DEMO_USER_ID = 1


@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Dashboard / data
# ---------------------------------------------------------------------------
@app.route("/api/dashboard/<int:user_id>")
def dashboard(user_id):
    user = db.get_user(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify({
        "user": user,
        "accounts": db.get_accounts(user_id),
        "schedules": db.get_schedules(user_id),
        "transactions": db.get_transactions(user_id, limit=15),
    })


# ---------------------------------------------------------------------------
# Multi-agent pipeline
# ---------------------------------------------------------------------------
@app.route("/api/run-pipeline/<int:user_id>", methods=["POST"])
def run_pipeline(user_id):
    """Runs the full Observer -> Insight -> Decision -> Action pipeline
    and returns the nudges that were delivered, plus a trace of what each
    agent did (for the 'agent activity' panel in the UI)."""
    cache.clear_pipeline_log(user_id)

    events = observer_agent.run(user_id)
    insights = insight_agent.run(user_id, events)
    decisions = decision_agent.run(user_id, insights)
    delivered = action_agent.prepare(user_id, decisions)

    return jsonify({
        "events_found": len(events),
        "insights_generated": len(insights),
        "nudges_delivered": delivered,
        "nudges_suppressed": [d for d in decisions if d["decision"] == "suppressed"],
        "pipeline_trace": cache.get_pipeline_log(user_id),
    })


@app.route("/api/nudges/<int:user_id>")
def get_nudges(user_id):
    return jsonify(db.get_active_nudges(user_id))


@app.route("/api/pipeline-trace/<int:user_id>")
def pipeline_trace(user_id):
    return jsonify(cache.get_pipeline_log(user_id))


# ---------------------------------------------------------------------------
# User acting on a nudge  (closes the loop back through Action Agent)
# ---------------------------------------------------------------------------
@app.route("/api/nudges/<int:nudge_id>/accept", methods=["POST"])
def accept_nudge(nudge_id):
    result = action_agent.execute(nudge_id)
    return jsonify(result)


@app.route("/api/nudges/<int:nudge_id>/dismiss", methods=["POST"])
def dismiss_nudge(nudge_id):
    nudge = db.get_nudge(nudge_id)
    if not nudge:
        return jsonify({"error": "not found"}), 404
    result = feedback_loop.collect(nudge_id, nudge["user_id"], "dismissed")
    return jsonify(result)


@app.route("/api/feedback-stats/<int:user_id>")
def feedback_stats(user_id):
    return jsonify(feedback_loop.stats(user_id))


# ---------------------------------------------------------------------------
# Demo utility — reset seed data
# ---------------------------------------------------------------------------
@app.route("/api/reset/<int:user_id>", methods=["POST"])
def reset(user_id):
    db.init_db(reset=True)
    cache.clear_pipeline_log(user_id)
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
