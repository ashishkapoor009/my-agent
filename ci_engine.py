"""
ci_engine.py - Core Orchestrator for the Continuous Improvement Value Stream Leader AI.

Integrates all 6 Memory Architectures:
1. Conversation History (Multi-turn conversational flow)
2. Checkpointer with thread-id (Switchable InMemorySaver vs SqliteSaver)
3. Durable Memory (Profile & Value Stream context persisted in JSON)
4. Semantic Memory (Institutional Kaizen knowledge base vector retrieval)
5. Procedural Memory (Lean Six Sigma & Kaizen playbooks with progressive disclosure)
6. Efficient Context Management (Context Packet with sliding window & running summary)
"""

import datetime
import os
import sqlite3
from typing import Dict, Any, List, Tuple

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from ci_durable_memory import (
    load_profile,
    update_profile,
    profile_as_prompt_text,
    PROFILE_FILE,
)
from ci_semantic_memory import (
    search_semantic_memory,
    format_semantic_context,
    load_knowledge_base,
)
from ci_skills_loader import (
    load_skills,
    choose_skill,
)

load_dotenv()


def sync_secrets():
    """Ensure environment variables are populated from .env, Streamlit secrets, and aliases."""
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            for k in [
                "DEEPSEEK_API_KEY", "deepseek_api_key",
                "AI_API_KEY", "ai_api_key",
                "OPENAI_API_KEY", "openai_api_key",
                "AI_BASE_URL", "ai_base_url",
                "DEEPSEEK_API_BASE", "deepseek_api_base",
            ]:
                if k in st.secrets:
                    val = str(st.secrets[k]).strip()
                    if val:
                        os.environ[k.upper()] = val
            for k, v in st.secrets.items():
                if isinstance(v, str) and k.upper() not in os.environ and v.strip():
                    os.environ[k.upper()] = v.strip()
    except Exception:
        pass

    # Alias handling: if DEEPSEEK_API_KEY is not set, map from AI_API_KEY or OPENAI_API_KEY
    if not os.getenv("DEEPSEEK_API_KEY"):
        if os.getenv("AI_API_KEY"):
            os.environ["DEEPSEEK_API_KEY"] = os.environ["AI_API_KEY"]
        elif os.getenv("OPENAI_API_KEY"):
            os.environ["DEEPSEEK_API_KEY"] = os.environ["OPENAI_API_KEY"]

    if not os.getenv("DEEPSEEK_API_BASE") and os.getenv("AI_BASE_URL"):
        os.environ["DEEPSEEK_API_BASE"] = os.environ["AI_BASE_URL"]


sync_secrets()

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ci_conversations.sqlite")
MAX_RECENT_TURNS = 4  # 2 user turns + 2 assistant turns

# SQLite persistent connection
sqlite_conn = sqlite3.connect(DB_FILE, check_same_thread=False)
sqlite_checkpointer = SqliteSaver(sqlite_conn)
inmemory_checkpointer = InMemorySaver()

# Lazy-loaded DeepSeek models to prevent import-time crashes if keys are loading
_chat_model = None
_fast_model = None


def get_chat_model():
    """Lazily initialize or return the primary answerer chat model."""
    global _chat_model
    if _chat_model is None:
        sync_secrets()
        api_key = os.getenv("DEEPSEEK_API_KEY")
        api_base = os.getenv("DEEPSEEK_API_BASE")
        kwargs = {"temperature": 0.2, "max_tokens": 1000}
        if api_key:
            kwargs["api_key"] = api_key
        if api_base:
            kwargs["api_base"] = api_base
        _chat_model = init_chat_model("deepseek:deepseek-chat", **kwargs)
    return _chat_model


def get_fast_model():
    """Lazily initialize or return the fast chooser/extractor model."""
    global _fast_model
    if _fast_model is None:
        sync_secrets()
        api_key = os.getenv("DEEPSEEK_API_KEY")
        api_base = os.getenv("DEEPSEEK_API_BASE")
        kwargs = {"temperature": 0.0, "max_tokens": 150}
        if api_key:
            kwargs["api_key"] = api_key
        if api_base:
            kwargs["api_base"] = api_base
        _fast_model = init_chat_model("deepseek:deepseek-chat", **kwargs)
    return _fast_model


# Procedural skills
ci_skills = load_skills()

# In-memory tracking for context management and running summaries per thread
thread_recent: Dict[str, List[Dict[str, str]]] = {}
thread_summaries: Dict[str, str] = {}
thread_full_history: Dict[str, List[Dict[str, str]]] = {}


def estimate_tokens(text: str) -> int:
    """Approximate token count (1 token ≈ 4 characters)."""
    return max(1, len(text) // 4)


def fold_into_executive_summary(current_summary: str, old_messages: List[Dict[str, str]]) -> str:
    """
    Summarize older dialogue turns into a dense Lean Six Sigma executive brief.
    Preserves numerical metrics, stations, bottleneck machines, root causes, and action owners.
    """
    lines = []
    for msg in old_messages:
        role = "Leader" if msg["role"] == "user" else "CI Copilot"
        lines.append(f"{role}: {msg['content']}")
    dialogue_chunk = "\n".join(lines)

    summary_input = current_summary if current_summary else "No prior history."
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an executive recorder for a Continuous Improvement Value Stream Leader. "
                "Update the running summary with new dialogue lines. "
                "CRITICAL: Always retain all specific operational metrics (takt times, cycle times, PCE %, scrap $, defect PPM, lead times), "
                "specific equipment/cell identifiers, identified root causes, and agreed countermeasures. "
                "Keep it dense and factual (3-4 bullet sentences maximum)."
            )
        },
        {
            "role": "user",
            "content": f"Existing Summary:\n{summary_input}\n\nNew Dialogue Lines to Fold In:\n{dialogue_chunk}"
        }
    ]

    try:
        res = get_fast_model().invoke(prompt)
        return res.content.strip()
    except Exception:
        return current_summary


def get_checkpointer(checkpointer_type: str):
    """Return the requested checkpointer instance."""
    if checkpointer_type.lower().startswith("inmemory"):
        return inmemory_checkpointer
    return sqlite_checkpointer


def list_sqlite_threads() -> List[str]:
    """Inspect SQLite database to list existing thread IDs."""
    try:
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT DISTINCT thread_id FROM checkpoints ORDER BY thread_id")
        rows = cursor.fetchall()
        return [r[0] for r in rows if r[0]]
    except Exception:
        return []


def load_thread_history(thread_id: str, checkpointer_type: str = "SqliteSaver") -> List[Dict[str, str]]:
    """Retrieve message history for a given thread_id from the checkpointer."""
    cp = get_checkpointer(checkpointer_type)
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = cp.get(config)
        if state and "channel_values" in state:
            messages = state["channel_values"].get("messages", [])
            formatted = []
            for m in messages:
                role = "user" if getattr(m, "type", "") == "human" or (isinstance(m, dict) and m.get("role") == "user") else "assistant"
                content = getattr(m, "content", "") if not isinstance(m, dict) else m.get("content", "")
                if content:
                    formatted.append({"role": role, "content": content})
            return formatted
    except Exception:
        pass
    return thread_recent.get(thread_id, [])


def execute_ci_turn(
    message: str,
    thread_id: str,
    checkpointer_type: str = "SqliteSaver",
    use_durable_memory: bool = True,
    use_semantic_memory: bool = True,
    use_procedural_memory: bool = True,
    use_context_compression: bool = True,
) -> Tuple[str, Dict[str, Any]]:
    """
    Execute a turn for the Continuous Improvement Value Stream Leader.
    Orchestrates all 6 memory layers and returns (response_text, telemetry_data).
    """
    today_str = datetime.date.today().strftime("%d %B %Y")
    
    # Initialize thread tracking
    if thread_id not in thread_recent:
        thread_recent[thread_id] = []
        thread_summaries[thread_id] = ""
        thread_full_history[thread_id] = []

    # -------------------------------------------------------------
    # 1. BASE SYSTEM PERSONA
    # -------------------------------------------------------------
    base_system = (
        f"You are the Senior Continuous Improvement (CI) Value Stream AI Copilot. Today is {today_str}.\n"
        "You assist the Continuous Improvement Value Stream Leader in achieving operational excellence, "
        "eliminating the 8 wastes (DOWNTIME), optimizing Value Stream Maps, leading DMAIC projects, "
        "and driving measurable safety, quality, delivery, cost, and morale (SQDCM) gains.\n"
        "Guidelines:\n"
        "- Ground your insights in Lean principles (Toyota Production System, Shingo Model, Six Sigma).\n"
        "- Be data-driven, practical, and action-oriented.\n"
        "- Use clean formatting with clear headings, bullet points, and markdown tables where appropriate.\n"
    )

    # -------------------------------------------------------------
    # 2. DURABLE MEMORY (Profile & Value Stream Context)
    # -------------------------------------------------------------
    durable_text = ""
    new_facts = {}
    profile = load_profile()
    if use_durable_memory:
        profile, new_facts = update_profile(message, model=get_fast_model())
        durable_text = profile_as_prompt_text(profile)

    # -------------------------------------------------------------
    # 3. SEMANTIC MEMORY (Institutional Kaizen Knowledge Base)
    # -------------------------------------------------------------
    semantic_text = ""
    matched_cases = []
    if use_semantic_memory:
        matched_cases = search_semantic_memory(message, top_k=2, min_score=0.15)
        if matched_cases:
            semantic_text = format_semantic_context(matched_cases)

    # -------------------------------------------------------------
    # 4. PROCEDURAL MEMORY (Skills / Playbooks with Progressive Disclosure)
    # -------------------------------------------------------------
    chosen_skill = None
    procedural_text = ""
    if use_procedural_memory:
        chosen_skill = choose_skill(get_fast_model(), ci_skills, message)
        if chosen_skill:
            procedural_text = (
                f"\n--- STANDARD OPERATING PROCEDURE (Procedural Memory: {chosen_skill['name']}) ---\n"
                f"Follow this validated standard work procedure strictly:\n\n{chosen_skill['body']}\n"
                "--- END OF PROCEDURE ---\n"
            )

    # -------------------------------------------------------------
    # 5. ASSEMBLE SYSTEM PROMPT
    # -------------------------------------------------------------
    full_prompt = base_system
    if durable_text:
        full_prompt += durable_text
    if semantic_text:
        full_prompt += semantic_text
    if procedural_text:
        full_prompt += procedural_text

    # -------------------------------------------------------------
    # 6. CONTEXT MANAGEMENT & RUNNING SUMMARY
    # -------------------------------------------------------------
    running_summary = thread_summaries.get(thread_id, "")
    recent_history = thread_recent.get(thread_id, [])

    if use_context_compression and running_summary:
        full_prompt += f"\nExecutive Summary of Earlier Project Turns:\n{running_summary}\n"

    new_user_msg = {"role": "user", "content": message}

    if use_context_compression:
        messages_to_send = [{"role": "system", "content": full_prompt}] + recent_history + [new_user_msg]
    else:
        # Full uncompressed history
        messages_to_send = [{"role": "system", "content": full_prompt}] + thread_full_history[thread_id] + [new_user_msg]

    # Calculate token counts
    sent_text = "".join(m["content"] for m in messages_to_send)
    tokens_sent = estimate_tokens(sent_text)

    # Baseline: What sending uncompressed history + full playbook library would cost
    all_skills_size = sum(len(s["body"]) for s in ci_skills)
    uncompressed_history_text = "".join(m["content"] for m in thread_full_history[thread_id]) + message
    uncompressed_total_text = base_system + durable_text + semantic_text + ("x" * all_skills_size) + uncompressed_history_text
    tokens_uncompressed = estimate_tokens(uncompressed_total_text)

    # -------------------------------------------------------------
    # INVOKE DEEPSEEK
    # -------------------------------------------------------------
    try:
        ai_reply = get_chat_model().invoke(messages_to_send)
        reply_content = ai_reply.content.strip()
    except Exception as e:
        reply_content = f"Error communicating with DeepSeek API: {str(e)}"

    new_asst_msg = {"role": "assistant", "content": reply_content}

    # -------------------------------------------------------------
    # UPDATE CHECKPOINTER & RECENT BUFFERS
    # -------------------------------------------------------------
    # Save to thread history tracking
    thread_recent[thread_id].append(new_user_msg)
    thread_recent[thread_id].append(new_asst_msg)
    thread_full_history[thread_id].append(new_user_msg)
    thread_full_history[thread_id].append(new_asst_msg)

    # Checkpointer checkpointing (LangGraph checkpointer persistence)
    cp = get_checkpointer(checkpointer_type)
    config = {"configurable": {"thread_id": thread_id}}
    try:
        # Store state into checkpointer for thread persistence
        cp.put(
            config,
            {"messages": thread_full_history[thread_id]},
            {"step": len(thread_full_history[thread_id]) // 2},
            {}
        )
    except Exception:
        pass

    # Fold oldest turns if recent buffer exceeds limit
    folded_this_turn = False
    if use_context_compression:
        while len(thread_recent[thread_id]) > MAX_RECENT_TURNS:
            oldest_pair = thread_recent[thread_id][:2]
            thread_recent[thread_id] = thread_recent[thread_id][2:]
            thread_summaries[thread_id] = fold_into_executive_summary(
                thread_summaries[thread_id], oldest_pair
            )
            folded_this_turn = True

    # Build detailed telemetry for the UI inspector
    tokens_saved = max(0, tokens_uncompressed - tokens_sent)
    percent_saved = round((tokens_saved / tokens_uncompressed) * 100, 1) if tokens_uncompressed > 0 else 0

    telemetry = {
        "thread_id": thread_id,
        "checkpointer_type": checkpointer_type,
        "tokens_sent": tokens_sent,
        "tokens_uncompressed": tokens_uncompressed,
        "tokens_saved": tokens_saved,
        "percent_saved": percent_saved,
        "chosen_skill": chosen_skill,
        "matched_cases": matched_cases,
        "new_facts": new_facts,
        "profile": profile,
        "running_summary": thread_summaries.get(thread_id, ""),
        "recent_count": len(thread_recent[thread_id]),
        "total_thread_turns": len(thread_full_history[thread_id]) // 2,
        "folded_this_turn": folded_this_turn,
        "raw_prompt_segments": {
            "base_system": base_system,
            "durable_profile": durable_text,
            "semantic_memory": semantic_text,
            "procedural_skill": procedural_text,
            "running_summary": running_summary,
            "recent_messages_count": len(thread_recent[thread_id]) - 2,
        }
    }

    return reply_content, telemetry


def reset_thread(thread_id: str):
    """Clear memory for a specific thread."""
    if thread_id in thread_recent:
        thread_recent[thread_id] = []
    if thread_id in thread_summaries:
        thread_summaries[thread_id] = ""
    if thread_id in thread_full_history:
        thread_full_history[thread_id] = []


def reset_profile():
    """Wipe durable profile file to start fresh."""
    empty = {f: "" for f in load_profile().keys()}
    save_profile(empty)
    return empty

