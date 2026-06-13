# AI Chatbot with Personality and Long-term Memory

A production-ready AI chatbot built as **Project 23** in the AI Solution Architecture learning series. Unlike all previous chatbots, this one remembers facts about you permanently across sessions, builds on past conversations, and responds with a distinct personality tailored to your preferences.

---

## Where this fits in the AI development lifecycle

```
1-22. All previous projects    ✅
23.   AI Chatbot + Memory      ← this project (persistent memory + personality)
24.   Docker + AWS             Upcoming
```

---

## What Makes This Different from All Previous Chatbots

| Feature | Previous chatbots | This chatbot |
|---|---|---|
| Memory duration | Session only — forgotten on close | Permanent — stored in SQLite |
| Personalisation | Generic responses to everyone | Tailored to your history and preferences |
| Personality | Neutral, generic | 4 distinct characters to choose from |
| Conversation continuity | Start fresh every time | Each conversation builds on the last |
| Self-improvement | Static | Gets better the more you talk to it |

---

## The 3 Types of Memory

### Short-term memory (session history)
Last 8 messages in the current conversation. Same as all previous projects. Forgotten when session ends.

### Long-term memory (permanent facts)
Specific facts about the user extracted automatically from every conversation and stored in SQLite.

```
PROFESSIONAL:
  - Works as AI engineer at TechCorp
  - Building a RAG system with Qwen2.5-VL
  - Prefers Python over JavaScript

PREFERENCES:
  - Likes concise answers without filler
  - Prefers code examples over theory

GOALS:
  - Wants to become a senior AI architect
  - Learning Docker and AWS next
```

### Episodic memory (conversation summaries)
Each conversation is summarised when it ends and stored for future reference.

```
June 12, 2026: Nikhil asked about RAG chunking strategies.
               Discussed fixed vs semantic chunking. Decided to
               try paragraph chunking for HR documents.
```

---

## The 4 Personalities

| Personality | Emoji | Best for | Style |
|---|---|---|---|
| Aria — Professional Assistant | 👩‍💼 | Work tasks, productivity | Efficient, structured, warm |
| Max — Casual Friend | 😎 | Casual chat, brainstorming | Friendly, humorous, relatable |
| Sage — Deep Thinker | 🦉 | Complex problems, learning | Thoughtful, philosophical, curious |
| Coach — Motivational Mentor | 🏆 | Goals, accountability | Energetic, action-oriented, encouraging |

---

## Project Structure

```
memory_chatbot/
│
├── chatbot_app.py       # Streamlit UI — main entry point
├── chatbot.py           # main chatbot logic + LLM calls
├── memory_store.py      # SQLite database operations
├── memory_extractor.py  # extract facts from conversation with Qwen
├── personality.py       # 4 bot personality definitions
│
├── chatbot.db           # auto-created SQLite database
│
└── requirements.txt
```

---

## Prerequisites

- Python 3.9+
- Virtual environment activated
- Ollama running on remote GPU at `http://10.22.39.192:11434`
- Model `qwen2.5vl:latest` pulled on the remote GPU
- `sqlite3` — built into Python, no install needed

---

## Installation

```powershell
cd memory_chatbot

# Activate venv
C:\Dev\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### `requirements.txt`

```
streamlit
requests
python-dotenv
```

---

## Running the App

```powershell
cd "C:\Users\amith\Desktop\Confidential\Misc Projects\P3\memory_chatbot"
C:\Dev\venv\Scripts\Activate.ps1
streamlit run chatbot_app.py
```

Open `http://localhost:8501`.

---

## How to Use

### Step 1 — Enter your name
Type your name in the sidebar. This creates your user profile and links all memories to you.

### Step 2 — Choose a personality
Click any of the 4 personality buttons. You can switch mid-conversation.

### Step 3 — Chat and share about yourself
The bot automatically extracts facts as you talk:
```
"I work as a data scientist at Infosys"     → saves to PROFESSIONAL
"I prefer R over Python for statistics"     → saves to PREFERENCES
"I'm trying to learn machine learning"      → saves to GOALS
"Please keep answers under 3 sentences"     → saves to INTERACTIONS
```

### Step 4 — Start a new conversation
Click **New conversation** — the current session is summarised and saved. Next time you chat, the bot remembers everything.

### Step 5 — View and manage memories
Go to the **My Memory** tab to see all stored facts. Delete any memory you don't want.

---

## Memory Flow — What Happens Per Message

```
You send a message
        ↓
chatbot.py builds system prompt:
  personality instructions
  + all long-term memories about you
  + past conversation summaries
  + recent session history
        ↓
Qwen generates response (temperature 0.7 for natural conversation)
        ↓
memory_extractor.py analyses exchange:
  "Did the user reveal any facts about themselves?"
  → extracts structured facts as JSON
        ↓
New facts saved to SQLite memories table
        ↓
Response shown with "💾 N new memories saved" indicator
        ↓
When you click "New conversation":
  summarise_conversation() called
  Summary saved to conversations table
```

---

## Database Schema

### users table
```sql
id          TEXT PRIMARY KEY    -- short UUID
name        TEXT                -- display name
created_at  TEXT                -- ISO timestamp
message_count INTEGER           -- total messages sent
```

### memories table
```sql
id          INTEGER PRIMARY KEY
user_id     TEXT                -- links to users
category    TEXT                -- personal/professional/preferences/goals/context/interactions
fact        TEXT                -- the actual memory
confidence  REAL                -- 0.0 to 1.0
created_at  TEXT
updated_at  TEXT                -- refreshed when fact confirmed again
```

### conversations table
```sql
id            INTEGER PRIMARY KEY
user_id       TEXT
session_id    TEXT
summary       TEXT              -- AI-generated 2-3 sentence summary
message_count INTEGER
started_at    TEXT
ended_at      TEXT
```

### messages table
```sql
id          INTEGER PRIMARY KEY
user_id     TEXT
session_id  TEXT
role        TEXT                -- user or assistant
content     TEXT
timestamp   TEXT
```

---

## Memory Categories

| Category | What gets stored |
|---|---|
| personal | Name, age, location, family |
| professional | Job title, company, skills, tech stack |
| preferences | Likes, dislikes, favourite tools/languages |
| goals | What they want to learn or achieve |
| context | Current projects, active challenges |
| interactions | How they prefer the bot to communicate |

---

## Seeing Memory Work — Step by Step Demo

**Conversation 1:**
```
You: Hi, I'm Nikhil. I'm an AI engineer at TechCorp in Mumbai.
You: I'm currently building a RAG system. I use Python and prefer concise answers.
Bot: Great to meet you Nikhil! Your RAG work sounds fascinating...

[Click "New conversation"]
→ Conversation summarised and saved
```

**Conversation 2 (fresh session):**
```
You: What should I focus on next in my AI learning?

Bot: "Given your experience building RAG systems at TechCorp, Nikhil,
     and your Python background, I'd suggest exploring Knowledge Graphs
     or GraphRAG as a natural next step. It would complement what
     you're already doing..."

← Bot referenced your job, your project, and your location
  without you mentioning them again
```

**My Memory tab shows:**
```
PROFESSIONAL:
  - AI engineer at TechCorp in Mumbai
  - Currently building a RAG system

PREFERENCES:
  - Uses Python
  - Prefers concise answers

INTERACTIONS:
  - Wants direct answers without filler
```

---

## Common Questions

**Does memory persist if I restart Streamlit?**
Yes. All memories are stored in `chatbot.db` (SQLite file on disk). Restarting the app does not delete memories.

**Can I use this as multiple users?**
Each session generates a unique user ID. To be recognised as the same user across sessions, copy your user ID from the sidebar and paste it back in future sessions. (For production, add proper login — see Project 7.)

**How do I reset all memories?**
Delete `chatbot.db` and restart the app. Or delete individual memories in the **My Memory** tab.

**Will the bot always reference memories?**
No — it uses memories naturally when relevant, not robotically. Saying "Given your work on RAG..." feels natural. Listing all facts every reply would feel robotic.

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `sqlite3.OperationalError` | DB file locked | Close other connections, restart app |
| Memory not extracted | LLM returned non-JSON | Normal — happens occasionally, next message retries |
| Personality not changing | Old session cached | Click "New conversation" to apply personality |
| `Ollama connection error` | Remote GPU not reachable | Check `curl http://10.22.39.192:11434/api/tags` |

---

## Extending the Project

### Add user login (connect to Project 7 auth)

```python
# In chatbot_app.py — replace UUID user_id with authenticated user
from backend.auth import get_current_user

user = get_current_user(token)
st.session_state.user_id   = user["id"]
st.session_state.user_name = user["name"]
```

### Add memory search

```python
def search_memories(user_id: str, query: str) -> list[dict]:
    """Find memories relevant to a query using simple keyword match."""
    all_memories = get_memories(user_id, limit=100)
    query_lower  = query.lower()
    return [
        m for m in all_memories
        if any(word in m["fact"].lower()
               for word in query_lower.split()
               if len(word) > 3)
    ]
```

### Add memory importance scoring

```python
def score_memory_importance(fact: str) -> float:
    """Score how important a memory is (0-1)."""
    high_importance = ["works at", "lives in", "prefers", "allergic to", "goal is"]
    low_importance  = ["mentioned", "talked about", "asked about"]

    fact_lower = fact.lower()
    if any(h in fact_lower for h in high_importance):
        return 0.9
    if any(l in fact_lower for l in low_importance):
        return 0.4
    return 0.7
```

---

## Part of a Larger Project Series

| # | Project | Core skill learned |
|---|---|---|
| 7 | Production AI SaaS | Auth, database, user management |
| 11 | Streaming Chat | Real-time token display |
| 12 | AI Email Assistant | Multi-turn conversation |
| 23 | **AI Chatbot + Memory** | **Long-term memory, personality, episodic memory** |
| 24 | Docker + AWS | Containers, cloud deployment |

---

## Author

Built as part of an AI Solution Architecture learning project.
Model: `qwen2.5vl:latest` via Ollama on remote GPU `10.22.39.192:11434`
Memory: SQLite (local, persistent, no server needed)
No OpenAI · No Anthropic · Fully open source
