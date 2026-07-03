"""
Operational Database Layer
---------------------------
Stands in for the PostgreSQL "Operational Database" block in the FinPulse
architecture diagram. Stores User, Account, Transaction, and Schedule data.

In production this would be PostgreSQL. For the prototype we use SQLite so
the whole thing runs with zero external setup.
"""
import sqlite3
import os
import random
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "finpulse.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT,
    risk_profile TEXT DEFAULT 'moderate',
    kyc_verified INTEGER DEFAULT 1,
    consent_given INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    account_type TEXT,        -- savings, current, loan, card
    account_name TEXT,
    balance_available REAL,
    balance_locked REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id),
    txn_date TEXT,
    amount REAL,
    direction TEXT,            -- credit / debit
    channel TEXT,               -- UPI, IMPS, NEFT, POS, ONLINE
    category TEXT,               -- food, shopping, bills, salary, transfer, investment
    merchant TEXT
);

CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    schedule_type TEXT,        -- EMI, SIP, RD, BILL
    label TEXT,
    amount REAL,
    due_date TEXT,
    status TEXT DEFAULT 'upcoming'
);

CREATE TABLE IF NOT EXISTS nudges (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    agent_source TEXT,
    category TEXT,               -- idle_cash, upcoming_emi, spending_spike, goal_progress, low_balance
    title TEXT,
    message TEXT,
    relevance_score REAL,
    urgency_score REAL,
    final_score REAL,
    channel TEXT,
    action_type TEXT,           -- invest, pay_bill, start_sip, review, none
    action_payload TEXT,
    status TEXT DEFAULT 'active',   -- active, actioned, dismissed, suppressed
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY,
    nudge_id INTEGER REFERENCES nudges(id),
    user_id INTEGER,
    category TEXT,
    user_response TEXT,        -- accepted, dismissed, ignored
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS category_weights (
    user_id INTEGER,
    category TEXT,
    weight REAL DEFAULT 1.0,
    PRIMARY KEY (user_id, category)
);
"""


def init_db(reset=False):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if reset and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    cur = conn.execute("SELECT COUNT(*) as c FROM users")
    if cur.fetchone()["c"] == 0:
        _seed(conn)
    conn.close()


def _seed(conn):
    """Seed one demo user with realistic accounts, transactions and schedules."""
    conn.execute(
        "INSERT INTO users (id, name, phone, risk_profile, kyc_verified, consent_given) "
        "VALUES (1, 'Krishnav Agrawal', '98XXXXXX01', 'moderate', 1, 1)"
    )

    accounts = [
        (1, 1, 'savings', 'YONO Savings Account', 34500.0, 0.0),
        (2, 1, 'current', 'YONO Salary Account', 12000.0, 0.0),
        (3, 1, 'card', 'SBI Credit Card', -8400.0, 0.0),
    ]
    conn.executemany(
        "INSERT INTO accounts (id, user_id, account_type, account_name, balance_available, balance_locked) "
        "VALUES (?,?,?,?,?,?)",
        accounts,
    )

    # Transactions: mix of salary credit, everyday spends, and a long idle
    # balance pattern (no investment activity in 45 days) which the Observer
    # Agent is designed to pick up on.
    today = datetime.now()
    categories = [
        ("food", "Swiggy", "debit", "UPI"),
        ("shopping", "Amazon", "debit", "ONLINE"),
        ("transport", "Uber", "debit", "UPI"),
        ("bills", "Airtel Postpaid", "debit", "NEFT"),
        ("entertainment", "Netflix", "debit", "ONLINE"),
    ]
    txns = []
    txn_id = 1
    for i in range(60, 0, -3):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        cat, merch, direction, channel = random.choice(categories)
        amt = round(random.uniform(150, 2200), 2)
        txns.append((txn_id, 1, d, amt, direction, channel, cat, merch))
        txn_id += 1

    # Salary credits, monthly
    for i in [58, 28]:
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        txns.append((txn_id, 2, d, 45000.0, "credit", "NEFT", "salary", "Employer Pvt Ltd"))
        txn_id += 1

    conn.executemany(
        "INSERT INTO transactions (id, account_id, txn_date, amount, direction, channel, category, merchant) "
        "VALUES (?,?,?,?,?,?,?,?)",
        txns,
    )

    schedules = [
        (1, 1, 'EMI', 'Personal Loan EMI', 4500.0,
         (today + timedelta(days=4)).strftime("%Y-%m-%d"), 'upcoming'),
        (2, 1, 'BILL', 'Electricity Bill', 1850.0,
         (today + timedelta(days=6)).strftime("%Y-%m-%d"), 'upcoming'),
        (3, 1, 'SIP', 'Mutual Fund SIP (Paused)', 2000.0,
         (today + timedelta(days=10)).strftime("%Y-%m-%d"), 'paused'),
    ]
    conn.executemany(
        "INSERT INTO schedules (id, user_id, schedule_type, label, amount, due_date, status) "
        "VALUES (?,?,?,?,?,?,?)",
        schedules,
    )

    conn.commit()


def get_user(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_accounts(user_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM accounts WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_transactions(user_id, limit=200):
    conn = get_conn()
    rows = conn.execute(
        """SELECT t.* FROM transactions t
           JOIN accounts a ON t.account_id = a.id
           WHERE a.user_id=? ORDER BY t.txn_date DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_schedules(user_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM schedules WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_nudge(nudge):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO nudges
           (user_id, agent_source, category, title, message, relevance_score,
            urgency_score, final_score, channel, action_type, action_payload,
            status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            nudge["user_id"], nudge["agent_source"], nudge["category"],
            nudge["title"], nudge["message"], nudge["relevance_score"],
            nudge["urgency_score"], nudge["final_score"], nudge["channel"],
            nudge["action_type"], nudge.get("action_payload", ""),
            nudge.get("status", "active"), datetime.now().isoformat(),
        ),
    )
    conn.commit()
    nid = cur.lastrowid
    conn.close()
    return nid


def get_active_nudges(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM nudges WHERE user_id=? AND status='active' ORDER BY final_score DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_nudges(user_id, hours=24):
    """Used by the Decision Agent for frequency capping."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM nudges WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_nudge_status(nudge_id, status):
    conn = get_conn()
    conn.execute("UPDATE nudges SET status=? WHERE id=?", (status, nudge_id))
    conn.commit()
    conn.close()


def get_nudge(nudge_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM nudges WHERE id=?", (nudge_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def record_feedback(nudge_id, user_id, category, response):
    conn = get_conn()
    conn.execute(
        "INSERT INTO feedback (nudge_id, user_id, category, user_response, created_at) VALUES (?,?,?,?,?)",
        (nudge_id, user_id, category, response, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_feedback_stats(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT category, user_response, COUNT(*) as c FROM feedback WHERE user_id=? GROUP BY category, user_response",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_category_weight(user_id, category):
    conn = get_conn()
    row = conn.execute(
        "SELECT weight FROM category_weights WHERE user_id=? AND category=?",
        (user_id, category),
    ).fetchone()
    conn.close()
    return row["weight"] if row else 1.0


def adjust_category_weight(user_id, category, delta):
    conn = get_conn()
    existing = conn.execute(
        "SELECT weight FROM category_weights WHERE user_id=? AND category=?",
        (user_id, category),
    ).fetchone()
    if existing:
        new_weight = max(0.2, min(2.0, existing["weight"] + delta))
        conn.execute(
            "UPDATE category_weights SET weight=? WHERE user_id=? AND category=?",
            (new_weight, user_id, category),
        )
    else:
        new_weight = max(0.2, min(2.0, 1.0 + delta))
        conn.execute(
            "INSERT INTO category_weights (user_id, category, weight) VALUES (?,?,?)",
            (user_id, category, new_weight),
        )
    conn.commit()
    conn.close()
    return new_weight
