# memory_store.py
import sqlite3
import json
from datetime import datetime
from pathlib  import Path


DB_PATH = "chatbot.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables on first run."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          TEXT PRIMARY KEY,
            name        TEXT,
            created_at  TEXT,
            message_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS memories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT,
            category    TEXT,
            fact        TEXT,
            confidence  REAL DEFAULT 1.0,
            created_at  TEXT,
            updated_at  TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT,
            session_id  TEXT,
            summary     TEXT,
            message_count INTEGER,
            started_at  TEXT,
            ended_at    TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT,
            session_id  TEXT,
            role        TEXT,
            content     TEXT,
            timestamp   TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()


# ── User operations ───────────────────────────────────────────────────────────

def get_or_create_user(user_id: str, name: str = "") -> dict:
    conn = get_conn()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if not user:
        conn.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?)",
            (user_id, name or user_id, datetime.now().isoformat(), 0)
        )
        conn.commit()
        user = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()

    conn.close()
    return dict(user)


def increment_message_count(user_id: str):
    conn = get_conn()
    conn.execute(
        "UPDATE users SET message_count = message_count + 1 WHERE id = ?",
        (user_id,)
    )
    conn.commit()
    conn.close()


# ── Memory operations ─────────────────────────────────────────────────────────

MEMORY_CATEGORIES = [
    "personal",      # name, age, location, family
    "professional",  # job, company, skills, projects
    "preferences",   # likes, dislikes, communication style
    "goals",         # what they want to achieve
    "context",       # current projects, challenges
    "interactions"   # how they prefer to interact
]


def save_memory(user_id: str, category: str, fact: str, confidence: float = 1.0):
    """Save a new memory or update existing similar one."""
    conn = get_conn()
    now  = datetime.now().isoformat()

    # Check if similar memory exists
    existing = conn.execute(
        "SELECT id FROM memories WHERE user_id = ? AND category = ? AND fact = ?",
        (user_id, category, fact)
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE memories SET updated_at = ?, confidence = ? WHERE id = ?",
            (now, confidence, existing["id"])
        )
    else:
        conn.execute(
            "INSERT INTO memories (user_id, category, fact, confidence, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, category, fact, confidence, now, now)
        )

    conn.commit()
    conn.close()


def get_memories(user_id: str, category: str = None, limit: int = 20) -> list[dict]:
    """Retrieve memories for a user, optionally filtered by category."""
    conn  = get_conn()
    query = "SELECT * FROM memories WHERE user_id = ?"
    args  = [user_id]

    if category:
        query += " AND category = ?"
        args.append(category)

    query  += " ORDER BY updated_at DESC LIMIT ?"
    args.append(limit)

    rows = conn.execute(query, args).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_memories_text(user_id: str) -> str:
    """Format all memories as a text block for the system prompt."""
    memories = get_memories(user_id, limit=30)
    if not memories:
        return "No memories yet about this user."

    by_category = {}
    for m in memories:
        cat = m["category"]
        by_category.setdefault(cat, [])
        by_category[cat].append(m["fact"])

    lines = []
    for cat, facts in by_category.items():
        lines.append(f"{cat.upper()}:")
        for f in facts:
            lines.append(f"  - {f}")

    return "\n".join(lines)


def delete_memory(memory_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    conn.commit()
    conn.close()


# ── Message operations ────────────────────────────────────────────────────────

def save_message(user_id: str, session_id: str, role: str, content: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO messages (user_id, session_id, role, content, timestamp) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, session_id, role, content, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_recent_messages(user_id: str, session_id: str, limit: int = 10) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT role, content, timestamp FROM messages "
        "WHERE user_id = ? AND session_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (user_id, session_id, limit)
    ).fetchall()
    conn.close()
    return list(reversed([dict(r) for r in rows]))


# ── Conversation operations ───────────────────────────────────────────────────

def save_conversation_summary(
    user_id:       str,
    session_id:    str,
    summary:       str,
    message_count: int
):
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM conversations WHERE session_id = ?",
        (session_id,)
    ).fetchone()

    now = datetime.now().isoformat()
    if existing:
        conn.execute(
            "UPDATE conversations SET summary = ?, message_count = ?, ended_at = ? "
            "WHERE session_id = ?",
            (summary, message_count, now, session_id)
        )
    else:
        conn.execute(
            "INSERT INTO conversations "
            "(user_id, session_id, summary, message_count, started_at, ended_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, session_id, summary, message_count, now, now)
        )
    conn.commit()
    conn.close()


def get_past_conversations(user_id: str, limit: int = 5) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM conversations WHERE user_id = ? "
        "ORDER BY ended_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]