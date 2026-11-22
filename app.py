"""
app.py - Continuous Improvement (CI) Value Stream AI Copilot
Streamlit Application demonstrating all 6 Memory Architectures with LangChain and DeepSeek-Chat:
1. Conversation History
2. Checkpointers with Thread-ID (InMemorySaver vs SqliteSaver)
3. Durable Memory (Leader Profile & Operational Scope)
4. Semantic Memory (Institutional Kaizen A3 Knowledge Base Retrieval)
5. Procedural Memory (Playbooks with Progressive Disclosure)
6. Context Compression & Packet Management (Sliding Window + Running Summary)
"""

import json
import os
import streamlit as st
from dotenv import load_dotenv

from ci_engine import (
    execute_ci_turn,
    load_thread_history,
    list_sqlite_threads,
    reset_thread,
    reset_profile,
    ci_skills,
    thread_full_history,
    sync_secrets,
)
from ci_durable_memory import load_profile, PROFILE_FILE
from ci_semantic_memory import load_knowledge_base, search_semantic_memory

# Synchronize environment variables from Streamlit Cloud secrets
sync_secrets()

# Page Configuration
st.set_page_config(
    page_title="CI Value Stream AI Copilot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRESET_THREADS = [
    "VSM-AutoInverter-Line1",
    "Kaizen-SMED-Press04",
    "DMAIC-PowderCoat-Yield",
    "Gemba-PackCell-Flow",
    "RCA-Hydraulic-Spindle",
]

EXAMPLE_PROMPTS = [
    (
        "👤 Durable Profile",
        "I am Sridhar, Lean Six Sigma Master Black Belt leading the Automotive Electronics value stream at Chennai Plant 2. Our target Takt is 45s and target PCE is 25%."
    ),
    (
        "📐 VSM Calculation",
        "Analyze our VSM: Operating time is 450 mins/shift, customer demand is 480 units. Station cycle times: S1 Prep=32s, S2 Assembly=68s, S3 Inspection=40s, S4 Packaging=28s. What is our Takt and line constraint?"
    ),
    (
        "🧠 Semantic Search",
        "We are suffering huge changeover downtime on our stamping press taking 85 minutes between tool setups. Have we solved this before?"
    ),
    (
        "🔍 5-Whys RCA",
        "Run a 5-Whys on yesterday's breakdown: CNC Milling Spindle stalled during heavy cut, error code E-402, 45 minutes of line downtime."
    ),
    (
        "🚶 Gemba Walk",
        "Audit our warehouse packing area: Operators walk 8 km per shift fetching carton boxes and bubble wrap located 30 meters away, causing extreme fatigue and missing quotas."
    ),
]


def format_telemetry_markdown(tel):
    """Render telemetry metrics and context packet breakdown."""
    if not tel:
        return "### Context & Memory Telemetry\n*Send an operational query to inspect the live context packet.*"

    skill_info = "None (Answered from baseline knowledge)"
    if tel.get("chosen_skill"):
        s = tel["chosen_skill"]
        skill_info = f"**{s['name']}** (`ci_skills/{s['file']}`)"

    semantic_info = "None matched (No precedent met similarity threshold)"
    if tel.get("matched_cases"):
        lines = []
        for m in tel["matched_cases"]:
            c = m["case"]
            lines.append(f"- **[{c['id']}] {c['title']}** (Relevance: **{m['score']}%**)")
        semantic_info = "\n".join(lines)

    facts_info = "None extracted this turn."
    if tel.get("new_facts"):
        lines = [f"- **{k}**: {v}" for k, v in tel["new_facts"].items()]
        facts_info = "\n".join(lines)

    summary_info = tel.get("running_summary") or "*(No turns compressed yet; conversation is within the sliding window)*"

    tokens_sent = tel.get("tokens_sent", 0)
    tokens_uncompressed = tel.get("tokens_uncompressed", 0)
    tokens_saved = tel.get("tokens_saved", 0)
    pct_saved = tel.get("percent_saved", 0.0)

    md = f"""### 📊 Context Packet Telemetry

| Metric | Value |
| :--- | :--- |
| **Active Thread ID** | `{tel.get('thread_id')}` |
| **Checkpointer Engine** | `{tel.get('checkpointer_type')}` |
| **Tokens in Context Packet** | **~{tokens_sent} tokens** |
| **Full Uncompressed Cost** | ~{tokens_uncompressed} tokens |
| **Token Optimization** | **{pct_saved}% saved** (~{tokens_saved} spared) |
| **Thread Total Turns** | {tel.get('total_thread_turns', 0)} turns |

---

#### 1. 🛠️ Procedural Memory (Playbook)
{skill_info}

#### 2. 🧠 Semantic Memory (Kaizen Case Precedent)
{semantic_info}

#### 3. 👤 Durable Memory (Facts Extracted)
{facts_info}

#### 4. 📝 Running Executive Kaizen Summary
{summary_info}

#### 5. 🪟 Verbatim Sliding Window
- Recent turns sent word-for-word: **{tel.get('recent_count', 0) // 2} exchanges**
{"*(Old turns folded into executive summary)*" if tel.get("folded_this_turn") else ""}
"""
    return md


def get_profile_markdown():
    """Render the current durable profile state."""
    profile = load_profile()
    lines = ["### 👤 Durable Leader Profile (`ci_leader_profile.json`)\n"]
    lines.append("*Persists across all threads, sessions, and system restarts.*\n")
    lines.append("| Field | Recorded Fact |")
    lines.append("| :--- | :--- |")
    labels = {
        "leader_name": "Leader Name",
        "role_title": "Role / Title",
        "belt_level": "Belt Certification",
        "value_stream": "Assigned Value Stream",
        "facility_location": "Facility / Plant",
        "target_takt_time": "Target Takt Time",
        "target_pce": "Target Process Cycle Efficiency (PCE)",
        "primary_methodology": "Operational Methodology",
        "communication_preference": "Reporting Preference",
    }
    has_data = False
    for k, v in profile.items():
        if v:
            has_data = True
            lines.append(f"| **{labels.get(k, k)}** | {v} |")
        else:
            lines.append(f"| {labels.get(k, k)} | *(not yet stated)* |")

    if not has_data:
        lines.append("\n*No durable facts recorded yet. Introduce yourself with your belt level and value stream!*")
    return "\n".join(lines)


def get_checkpointer_status(thread_id, checkpointer_type):
    """Inspect checkpointer state for the active thread."""
    history = load_thread_history(thread_id, checkpointer_type)
    all_sqlite_threads = list_sqlite_threads()

    md = f"### 💾 Checkpointer Inspector\n\n"
    md += f"- **Current Engine**: `{checkpointer_type}`\n"
    md += f"- **Current Thread**: `{thread_id}`\n"
    md += f"- **Messages stored in thread**: **{len(history)} messages**\n\n"

    if "sqlite" in checkpointer_type.lower():
        md += "✅ **Storage mode**: Persistent SQLite (`ci_conversations.sqlite`). Preserved across server restarts.\n\n"
        md += f"**Discovered Threads in SQLite File ({len(all_sqlite_threads)}):**\n"
        for th in all_sqlite_threads:
            marker = "  *(Active)*" if th == thread_id else ""
            md += f"- `{th}`{marker}\n"
    else:
        md += "⚠️ **Storage mode**: In-Memory (`InMemorySaver`). Ephemeral RAM wiped on restart.\n\n"
    return md


# --- Session State Initialization ---
if "telemetry" not in st.session_state:
    st.session_state.telemetry = None
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# --- SIDEBAR: Controls & Memory Inspectors ---
with st.sidebar:
    st.title("⚙️ Memory Controls")

    cp_choice = st.radio(
        "Checkpointer Engine (Concept 2)",
        options=["SqliteSaver (Persistent on Disk)", "InMemorySaver (Volatile RAM)"],
        index=0,
    )
    cp_type = "SqliteSaver" if "sqlite" in cp_choice.lower() else "InMemorySaver"

    thread_option = st.selectbox(
        "Active Project Thread ID",
        options=PRESET_THREADS + ["Custom Thread..."],
        index=0,
    )
    if thread_option == "Custom Thread...":
        active_thread = st.text_input("Enter custom thread ID", value="Kaizen-NewProject-01").strip()
    else:
        active_thread = thread_option

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🗑️ Clear Thread"):
            reset_thread(active_thread)
            st.session_state.telemetry = None
            st.rerun()
    with col_btn2:
        if st.button("🔄 Reset Profile"):
            reset_profile()
            st.rerun()

    st.markdown("---")
    st.subheader("Memory Toggles")
    use_durable = st.checkbox("Durable Profile Memory (Concept 3)", value=True)
    use_semantic = st.checkbox("Semantic Kaizen Memory (Concept 4)", value=True)
    use_procedural = st.checkbox("Procedural Skills (Concept 5)", value=True)
    use_compression = st.checkbox("Context Compression (Concept 6)", value=True)

    st.markdown("---")
    with st.expander("👤 Durable Leader Profile", expanded=False):
        st.markdown(get_profile_markdown())

    with st.expander("💾 Checkpointer State", expanded=False):
        st.markdown(get_checkpointer_status(active_thread, cp_type))

    with st.expander("🧠 Search Kaizen Case Precedents", expanded=False):
        kb_query = st.text_input("Search A3 cases", placeholder="e.g., stamping, changeover, yield").strip()
        if kb_query:
            results = search_semantic_memory(kb_query, top_k=2)
            if results:
                for r in results:
                    c = r["case"]
                    st.markdown(f"**[{c['id']}] {c['title']}** (Score: {r['score']}%)")
                    st.markdown(f"*{c['problem']}*")
            else:
                st.caption("No matching precedent found.")
        else:
            all_cases = load_knowledge_base()
            st.caption(f"Knowledge Base contains {len(all_cases)} institutional cases.")

    with st.expander("🛠️ View Lean Playbooks (Skills)", expanded=False):
        skill_names = list(ci_skills.keys())
        chosen_s = st.selectbox("Playbook", options=skill_names)
        if chosen_s:
            st.markdown(ci_skills[chosen_s]["body"][:600] + "\n\n*(Truncated preview)*")


# --- MAIN CONTENT ---
st.title("⚡ Continuous Improvement (CI) Value Stream AI Copilot")
st.caption("Operational Excellence Decision Support Powered by LangChain, DeepSeek-Chat, and 6-Layer Memory Architecture")

if not os.getenv("DEEPSEEK_API_KEY"):
    st.warning("⚠️ **DeepSeek API Key is missing**: Please ensure `DEEPSEEK_API_KEY` (or `AI_API_KEY`) is pasted into Streamlit Cloud under **Manage app > Settings > Secrets**.")

with st.expander("🎯 How this App Implements All 6 Memory Concepts", expanded=False):
    st.markdown(
        """
        1. **Conversation History**: Multi-turn dialogue continuity stored in the active thread.
        2. **Checkpointer with thread-id**: Toggle between **`SqliteSaver`** (persists to disk, survives server restarts) and **`InMemorySaver`** (ephemeral RAM). Threads never leak into each other!
        3. **Durable Memory**: The CI Leader's identity, belt certification, plant location, and target KPIs persist across ALL threads in `ci_leader_profile.json`.
        4. **Semantic Memory**: Automatically searches 8 past Kaizen A3 cases using TF-IDF vector retrieval to benchmark solutions against institutional history.
        5. **Procedural Memory (Skills)**: Six Lean Six Sigma playbooks (`VSM`, `5-Whys`, `Gemba Waste`, `DMAIC Charter`, `SMED`, `Poka-Yoke`). The model sees only the menu, then loads the winner.
        6. **Context Management**: Context Packet architecture with a sliding window (last 4 turns) + running executive summary to eliminate context bloat and save 50-75% tokens!
        """
    )

# Example Chips
st.markdown("**Quick Prompts (Click to test memory systems):**")
cols = st.columns(len(EXAMPLE_PROMPTS))
for i, (label, prompt_text) in enumerate(EXAMPLE_PROMPTS):
    with cols[i]:
        if st.button(label, key=f"chip_{i}", use_container_width=True):
            st.session_state.pending_prompt = prompt_text
            st.rerun()

# Layout: Chat Column (Left) & Telemetry Column (Right)
col_chat, col_telemetry = st.columns([3, 2], gap="large")

with col_chat:
    st.subheader(f"💬 Project Thread: `{active_thread}`")

    # Load and display conversation history for the active thread
    history = load_thread_history(active_thread, cp_type)

    chat_container = st.container()
    with chat_container:
        if not history:
            st.info("👋 This project thread is empty. Ask a question or use an example prompt above!")
        else:
            for msg in history:
                role = "user" if msg["role"] == "user" else "assistant"
                with st.chat_message(role):
                    st.markdown(msg["content"])

    # Handle pending prompt from example buttons
    prompt = None
    if st.session_state.pending_prompt:
        prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None
    else:
        prompt = st.chat_input("Ask about VSM calculations, SMED changeovers, 5-Whys, or introduce yourself...")

    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing with Context Packet & Memory Layers..."):
                try:
                    reply, tel = execute_ci_turn(
                        user_message=prompt,
                        thread_id=active_thread,
                        checkpointer_type=cp_type,
                        use_durable=use_durable,
                        use_semantic=use_semantic,
                        use_procedural=use_procedural,
                        use_compression=use_compression,
                    )
                    st.markdown(reply)
                    st.session_state.telemetry = tel
                except Exception as e:
                    st.error(f"Execution Error: {str(e)}")

        st.rerun()

with col_telemetry:
    st.markdown(format_telemetry_markdown(st.session_state.telemetry))
