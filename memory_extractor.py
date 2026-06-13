# memory_extractor.py
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST  = os.getenv("OLLAMA_HOST",  "http://10.22.39.192:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5vl:latest")
FENCE        = "```"


def call_llm(prompt: str, max_tokens: int = 512) -> str:
    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model":   OLLAMA_MODEL,
            "prompt":  prompt,
            "stream":  False,
            "options": {"temperature": 0.0, "num_predict": max_tokens}
        },
        timeout=60
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


def extract_facts(user_message: str, bot_response: str) -> list[dict]:
    """
    Extract memorable facts about the user from a conversation exchange.
    Returns list of { category, fact, confidence }
    """
    prompt = (
        "You are a memory extraction system.\n"
        "Extract facts about the USER from this conversation exchange.\n"
        "Only extract clear, factual information the user revealed about themselves.\n\n"
        f"USER said: {user_message}\n"
        f"BOT replied: {bot_response}\n\n"
        "Categories: personal, professional, preferences, goals, context, interactions\n\n"
        "Examples of good facts:\n"
        '- "User\'s name is Nikhil" (personal)\n'
        '- "User works as an AI engineer at TechCorp" (professional)\n'
        '- "User prefers Python over JavaScript" (preferences)\n'
        '- "User is building a RAG system" (context)\n'
        '- "User wants concise answers" (interactions)\n\n'
        "If no clear facts about the user were revealed, return empty array.\n"
        "Do NOT extract facts about the topic discussed — only about the USER.\n\n"
        f"Respond ONLY in JSON:\n{FENCE}json\n"
        '[\n'
        '  {"category": "personal", "fact": "...", "confidence": 0.9}\n'
        ']\n'
        f"{FENCE}"
    )

    raw = call_llm(prompt)

    try:
        if FENCE in raw:
            parts = raw.split(FENCE)
            for part in parts:
                if part.startswith("json"):
                    raw = part[4:].strip()
                    break
                elif part.strip().startswith("["):
                    raw = part.strip()
                    break
        result = json.loads(raw.strip())
        return result if isinstance(result, list) else []
    except Exception:
        return []


def summarise_conversation(messages: list[dict]) -> str:
    """Summarise a conversation for episodic memory."""
    if not messages:
        return ""

    convo = "\n".join(
        f"{m['role'].upper()}: {m['content'][:200]}"
        for m in messages[-10:]
    )

    prompt = (
        "Summarise this conversation in 2-3 sentences.\n"
        "Focus on: what topics were discussed, what the user was trying to achieve, "
        "and any important conclusions or decisions made.\n\n"
        f"CONVERSATION:\n{convo}\n\n"
        "SUMMARY:"
    )

    return call_llm(prompt, max_tokens=200)