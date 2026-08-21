import os
import sqlite3
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(__file__), "drift_history.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drift_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            resource_address TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            field_changed TEXT NOT NULL,
            classification TEXT NOT NULL,
            reason TEXT,
            suggestion TEXT,
            action_taken TEXT NOT NULL,
            pr_url TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_drift(resource_address, resource_type, field_changed, classification, reason, suggestion, action_taken, pr_url=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO drift_events 
        (timestamp, resource_address, resource_type, field_changed, classification, reason, suggestion, action_taken, pr_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        resource_address,
        resource_type,
        field_changed,
        classification,
        reason,
        suggestion,
        action_taken,
        pr_url
    ))
    conn.commit()
    conn.close()


def get_recent_events(days=7):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, resource_address, field_changed, classification, reason, action_taken, pr_url
        FROM drift_events
        ORDER BY timestamp DESC
        LIMIT 50
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_summary():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM drift_events")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM drift_events WHERE classification = 'SAFE'")
    safe = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM drift_events WHERE classification = 'RISKY'")
    risky = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM drift_events WHERE action_taken = 'auto-fixed'")
    auto_fixed = cursor.fetchone()[0]

    conn.close()
    return {
        "total": total,
        "safe": safe,
        "risky": risky,
        "auto_fixed": auto_fixed
    }


def print_history():
    events = get_recent_events()
    summary = get_summary()

    print("\n========== TerraGuard Drift History ==========\n")
    print(f"Total events: {summary['total']}")
    print(f"Safe: {summary['safe']}  |  Risky: {summary['risky']}  |  Auto-fixed: {summary['auto_fixed']}")
    print(f"\n{'Timestamp':<22} {'Resource':<40} {'Field':<15} {'Class':<8} {'Action':<12}")
    print("-" * 100)

    for event in events:
        timestamp = event[0][:19]
        resource = event[1][:38]
        field = event[2][:13]
        classification = event[3]
        action = event[5]
        print(f"{timestamp:<22} {resource:<40} {field:<15} {classification:<8} {action:<12}")

    print()


# Initialize the database when this module is first imported
init_db()


if __name__ == "__main__":
    print_history()