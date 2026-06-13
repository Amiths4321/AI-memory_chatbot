# chatbot_app.py
# streamlit run chatbot_app.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uuid
import streamlit as st
from datetime import datetime
from chatbot      import chat, end_session, init_db
from memory_store import (
    get_or_create_user, get_memories, get_all_memories_text,
    get_past_conversations, delete_memory
)
from personality  import get_personality_names, get_personality

init_db()

st.set_page_config(
    page_title="AI Chatbot",
    page_icon="🧠",
    layout="wide"
)

# ── Session state ─────────────────────────────────────────────────────────────
if "user_id"     not in st.session_state:
    st.session_state.user_id     = str(uuid.uuid4())[:8]
if "session_id"  not in st.session_state:
    st.session_state.session_id  = str(uuid.uuid4())[:8]
if "messages"    not in st.session_state:
    st.session_state.messages    = []
if "user_name"   not in st.session_state:
    st.session_state.user_name   = ""
if "personality" not in st.session_state:
    st.session_state.personality = "Aria — Professional Assistant"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🧠 AI Chatbot")
    st.caption("Remembers you · Has personality · Gets smarter")

    st.divider()

    # User setup
    if not st.session_state.user_name:
        st.markdown("**What's your name?**")
        name_input = st.text_input("Your name:", placeholder="e.g. Nikhil")
        if name_input:
            st.session_state.user_name = name_input
            get_or_create_user(st.session_state.user_id, name_input)
            st.rerun()
    else:
        st.markdown(f"**Hello, {st.session_state.user_name}!**")
        user = get_or_create_user(
            st.session_state.user_id,
            st.session_state.user_name
        )
        st.caption(f"User ID: {st.session_state.user_id}")
        st.caption(f"Messages sent: {user.get('message_count', 0)}")

    st.divider()

    # Personality selector
    st.markdown("**Choose personality**")
    personality_names = get_personality_names()
    for pname in personality_names:
        p = get_personality(pname)
        selected = st.session_state.personality == pname
        if st.button(
            f"{p['emoji']} {p['name']} — {p['description']}",
            use_container_width = True,
            type = "primary" if selected else "secondary",
            key  = f"p_{pname}"
        ):
            st.session_state.personality = pname
            st.rerun()

    st.divider()

    # New conversation
    if st.button("New conversation", use_container_width=True):
        if st.session_state.messages:
            end_session(st.session_state.user_id, st.session_state.session_id)
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.session_state.messages   = []
        st.rerun()

# ── Main ──────────────────────────────────────────────────────────────────────
if not st.session_state.user_name:
    st.title("🧠 AI Chatbot with Memory")
    st.info("Enter your name in the sidebar to get started.")
    st.markdown("""
**What makes this special:**
- 🧠 Remembers facts about you permanently
- 💬 Builds on past conversations
- 🎭 4 distinct personalities to choose from
- 📚 Gets smarter the more you talk to it

Try saying:
- "My name is [your name] and I work as a [job]"
- "I prefer Python and I'm building an AI project"
- "I like concise answers"

Then start a new conversation — it will remember!
    """)
    st.stop()

p = get_personality(st.session_state.personality)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["💬 Chat", "🧠 My Memory", "📚 Past Conversations"])

# ── Tab 1: Chat ───────────────────────────────────────────────────────────────
with tab1:
    st.title(f"{p['emoji']} {p['name']}")
    st.caption(p["description"])

    # Memory indicator
    memories = get_memories(st.session_state.user_id)
    if memories:
        st.caption(f"🧠 {len(memories)} memories about you · Session: {st.session_state.session_id}")

    # Chat history
    for msg in st.session_state.messages:
        avatar = "🧑" if msg["role"] == "user" else p["emoji"]
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            if msg.get("new_memories"):
                with st.expander(f"💾 {len(msg['new_memories'])} new memory saved", expanded=False):
                    for m in msg["new_memories"]:
                        st.caption(f"[{m.get('category', '')}] {m.get('fact', '')}")

    # Input
    user_input = st.chat_input(f"Talk to {p['name']}...")

    if user_input:
        # Show user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_input)

        # Get response
        with st.chat_message("assistant", avatar=p["emoji"]):
            with st.spinner(f"{p['name']} is thinking..."):
                result = chat(
                    user_input,
                    st.session_state.user_id,
                    st.session_state.user_name,
                    st.session_state.session_id,
                    st.session_state.personality
                )

            st.markdown(result["response"])

            if result["new_memories"]:
                with st.expander(
                    f"💾 {len(result['new_memories'])} new memory saved",
                    expanded=False
                ):
                    for m in result["new_memories"]:
                        st.caption(f"[{m.get('category', '')}] {m.get('fact', '')}")

        st.session_state.messages.append({
            "role":         "assistant",
            "content":      result["response"],
            "new_memories": result["new_memories"]
        })

# ── Tab 2: Memory viewer ──────────────────────────────────────────────────────
with tab2:
    st.subheader(f"🧠 What {p['name']} knows about you")

    memories = get_memories(st.session_state.user_id)

    if not memories:
        st.info(
            "No memories yet. Start chatting and share things about yourself — "
            "your job, preferences, projects, goals. The bot will remember them."
        )
    else:
        st.caption(f"{len(memories)} total memories")

        # Group by category
        by_cat = {}
        for m in memories:
            by_cat.setdefault(m["category"], [])
            by_cat[m["category"]].append(m)

        for cat, mems in by_cat.items():
            st.markdown(f"**{cat.upper()}**")
            for m in mems:
                col1, col2 = st.columns([5, 1])
                col1.markdown(f"- {m['fact']}")
                if col2.button("🗑️", key=f"del_{m['id']}", help="Delete this memory"):
                    delete_memory(m["id"])
                    st.rerun()

        st.divider()

        # Raw memory text
        with st.expander("View as system prompt text"):
            st.text(get_all_memories_text(st.session_state.user_id))

# ── Tab 3: Past conversations ─────────────────────────────────────────────────
with tab3:
    st.subheader("📚 Conversation history")

    past = get_past_conversations(st.session_state.user_id)

    if not past:
        st.info(
            "No past conversations yet. "
            "Conversations are summarised and saved when you click 'New conversation'."
        )
    else:
        for convo in past:
            date    = convo.get("ended_at", "")[:10]
            count   = convo.get("message_count", 0)
            summary = convo.get("summary", "No summary available")

            with st.expander(f"📅 {date} — {count} messages"):
                st.markdown(summary)