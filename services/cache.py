"""
Cache / Queue Layer
--------------------
Stands in for the Redis "Cache / Queue" block: real-time event buffering,
session store, and a lightweight pub/sub used to pass events from the
Observer Agent to the Insight Agent, mirroring the Kafka/Redis Streams
ingestion layer in the architecture diagram.
"""
from collections import defaultdict, deque
import time

_event_stream = defaultdict(lambda: deque(maxlen=100))   # user_id -> recent events
_session_store = {}
_pipeline_log = defaultdict(list)  # user_id -> list of pipeline run traces


def publish_event(user_id, event):
    event["ts"] = time.time()
    _event_stream[user_id].append(event)
    return event


def get_recent_events(user_id, n=20):
    return list(_event_stream[user_id])[-n:]


def set_session(user_id, data):
    _session_store[user_id] = data


def get_session(user_id):
    return _session_store.get(user_id)


def log_pipeline_step(user_id, step_name, payload):
    """Keeps a trace of what each agent did on the last pipeline run —
    used to power the 'agent activity' panel in the UI so the multi-agent
    handoff is visible, not just the final nudge."""
    _pipeline_log[user_id].append({
        "step": step_name,
        "payload": payload,
        "ts": time.time(),
    })
    # keep last 40 entries only
    _pipeline_log[user_id] = _pipeline_log[user_id][-40:]


def get_pipeline_log(user_id):
    return _pipeline_log[user_id]


def clear_pipeline_log(user_id):
    _pipeline_log[user_id] = []
