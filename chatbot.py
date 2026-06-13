# chatbot.py
import os
import requests
from datetime  import datetime
from dotenv    import load_dotenv
from memory_store    import (
    init_db, get_or_create_user, increment_message_count,
    save_memory, get_all_memories_text, get_memories,
    save_message, get_recent_messages,
    save_conversation_summary, get_past_conversations
)
from memory_extractor import extract_facts, summarise_conversation
from personality      import get_personality

load_dotenv()
init_db()

OLLAMA_HOST  = os.getenv("OLLAMA_HOST",  "http://10.22.39.192:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5vl:latest")


def call_llm(prompt: str, max_tokens: int = 1024) -> str:
    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model":   OLLAMA_MODEL,
            "prompt":  prompt,
            "stream":  False,
            "options": {"temperature": 0.7, "num_predict": max_tokens}
        },
        timeout=120
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


def build_system_prompt(
    user_id:          str,
    user_name:        str,
    personality_name: str
) -> str:
    """Build the system prompt with personality + memories."""
    personality    = get_personality(personality_name)
    memories_text  = get_all_memories_text(user_id)
    past_convos    = get_past_conversations(user_id, limit=3)

    past_text = ""
    if past_convos:
        past_text = "\nPAST CONVERSATIONS:\n" + "\n".join(
            f"- {c['ended_at'][:10]}: {c['summary']}"
            for c in past_convos
            if c.get("summary")
        )

    return (
        f"{personality['system_prompt']}\n\n"
        f"The user's name is: {user_name}\n\n"
        f"WHAT YOU KNOW ABOUT {user_name.upper()}:\n"
        f"{memories_text}\n"
        f"{past_text}\n\n"
        f"Use this knowledge naturally in conversation — don't recite it back robotically.\n"
        f"If you learn new things about the user, incorporate them naturally.\n"
        f"Today's date: {datetime.now().strftime('%B %d, %Y')}"
    )


def chat(
    user_message:     str,
    user_id:          str,
    user_name:        str,
    session_id:       str,
    personality_name: str
) -> dict:
    """
    Process one message and return response + metadata.
    Handles: memory retrieval → LLM call → memory extraction → storage
    """
    # Get recent conversation history
    history      = get_recent_messages(user_id, session_id, limit=8)
    system_prompt = build_system_prompt(user_id, user_name, personality_name)

    # Build full prompt
    history_text = ""
    for msg in history:
        role          = user_name if msg["role"] == "user" else get_personality(personality_name)["name"]
        history_text += f"{role}: {msg['content']}\n\n"

    prompt = (
        f"SYSTEM:\n{system_prompt}\n\n"
        f"CONVERSATION HISTORY:\n{history_text}"
        f"{user_name}: {user_message}\n\n"
        f"{get_personality(personality_name)['name']}:"
    )

    # Get response
    response = call_llm(prompt)

    # Save messages
    save_message(user_id, session_id, "user",      user_message)
    save_message(user_id, session_id, "assistant", response)
    increment_message_count(user_id)

    # Extract and save new memories (async-style — don't block response)
    try:
        new_facts = extract_facts(user_message, response)
        for fact in new_facts:
            save_memory(
                user_id,
                fact.get("category", "context"),
                fact.get("fact", ""),
                fact.get("confidence", 0.8)
            )
    except Exception as e:
        print(f"Memory extraction error: {e}")
        new_facts = []

    return {
        "response":     response,
        "new_memories": new_facts,
        "personality":  personality_name
    }


def end_session(user_id: str, session_id: str):
    """Save conversation summary when session ends."""
    messages = get_recent_messages(user_id, session_id, limit=20)
    if messages:
        summary = summarise_conversation(messages)
        save_conversation_summary(user_id, session_id, summary, len(messages))