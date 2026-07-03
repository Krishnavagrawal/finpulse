"""
Feedback Loop
--------------
User Action/Ignore -> Feedback Collector -> Model Re-training & Optimization
-> Better Relevance & Timing.

For the prototype, "re-training" is a lightweight weight adjustment per
category per user rather than a full model retrain — same effect
(future nudges of a dismissed category score lower / accepted categories
score higher), demonstrated live within a single demo session.
"""
from services import database as db


def collect(nudge_id, user_id, response):
    """response: 'accepted' | 'dismissed'"""
    nudge = db.get_nudge(nudge_id)
    if not nudge:
        return {"status": "error", "message": "Nudge not found"}

    category = nudge["category"]
    db.record_feedback(nudge_id, user_id, category, response)

    if response == "dismissed":
        db.update_nudge_status(nudge_id, "dismissed")
        new_weight = db.adjust_category_weight(user_id, category, -0.2)
    else:
        db.update_nudge_status(nudge_id, "actioned")
        new_weight = db.adjust_category_weight(user_id, category, +0.15)

    return {
        "status": "ok",
        "category": category,
        "response": response,
        "new_relevance_weight": round(new_weight, 2),
    }


def stats(user_id):
    return db.get_feedback_stats(user_id)
