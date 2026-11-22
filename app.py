"""
app.py - Continuous Improvement (CI) Value Stream AI Copilot
A complete AI application demonstrating all 6 Memory Architectures with LangChain, DeepSeek-Chat, and Gradio:
1. Conversation History
2. Checkpointers with Thread-ID (InMemorySaver vs SqliteSaver)
3. Durable Memory (Leader Profile & Operational Scope)
4. Semantic Memory (Institutional Kaizen A3 Knowledge Base Retrieval)
5. Procedural Memory (Playbooks with Progressive Disclosure)
6. Context Compression & Packet Management (Sliding Window + Running Summary)
"""

import json
import os
import gradio as gr
from dotenv import load_dotenv

from ci_engine import (
    execute_ci_turn,
    load_thread_history,
    list_sqlite_threads,
    reset_thread,
    reset_profile,
    ci_skills,
    thread_full_history,
)
from ci_durable_memory import load_profile, PROFILE_FILE
from ci_semantic_memory import load_knowledge_base, search_semantic_memory

load_dotenv()

# Read secrets from Streamlit Cloud if deployed there
try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for k, v in st.secrets.items():
            if isinstance(v, str) and k not in os.environ:
                os.environ[k] = v
except Exception:
    pass


PRESET_THREADS = [
    "VSM-AutoInverter-Line1",
    "Kaizen-SMED-Press04",
    "DMAIC-PowderCoat-Yield",
    "Gemba-PackCell-Flow",
    "RCA-Hydraulic-Spindle",
]

# Quick example prompts
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
    """Render the telemetry metrics and context packet breakdown."""
    if not tel:
        return "### Context & Memory Telemetry\n*Send a message to inspect the live context packet.*"

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

    summary_info = tel.get("running_summary") or "*(No turns compressed yet; conversation is inside the sliding window)*"

    tokens_sent = tel.get("tokens_sent", 0)
    tokens_uncompressed = tel.get("tokens_uncompressed", 0)
    tokens_saved = tel.get("tokens_saved", 0)
    pct_saved = tel.get("percent_saved", 0.0)

    md = f"""### 📊 Context Packet Telemetry & Memory Breakdown

| Metric | Value |
| :--- | :--- |
| **Active Thread ID** | `{tel.get('thread_id')}` |
| **Checkpointer Engine** | `{tel.get('checkpointer_type')}` |
| **Tokens in Context Packet** | **~{tokens_sent} tokens** |
| **Full Uncompressed Cost** | ~{tokens_uncompressed} tokens |
| **Token Optimization** | **{pct_saved}% saved** (~{tokens_saved} tokens spared) |
| **Thread Total Turns** | {tel.get('total_thread_turns', 0)} turns |

---

#### 1. 🛠️ Procedural Memory (Playbook Chosen)
{skill_info}

#### 2. 🧠 Semantic Memory (Kaizen Knowledge Base Retrieval)
{semantic_info}

#### 3. 👤 Durable Memory (Facts Updated This Turn)
{facts_info}

#### 4. 📝 Running Executive Kaizen Summary (Compressed Older Turns)
{summary_info}

#### 5. 🪟 Verbatim Sliding Window
- Recent turns sent word-for-word: **{tel.get('recent_count', 0) // 2} exchanges**
{"*(Oldest turns folded into summary this turn)*" if tel.get("folded_this_turn") else ""}
"""
    return md


def get_profile_markdown():
    """Render the current durable profile state."""
    profile = load_profile()
    lines = ["### 👤 Durable Profile (`ci_leader_profile.json`)\n"]
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
        lines.append("\n*No durable facts recorded yet. Tell the agent your name, belt certification, or value stream!*")
    return "\n".join(lines)


def get_checkpointer_status(thread_id, checkpointer_type):
    """Inspect checkpointer state for the active thread."""
    history = load_thread_history(thread_id, checkpointer_type)
    all_sqlite_threads = list_sqlite_threads()
    
    md = f"### 💾 Checkpointer State Inspector\n\n"
    md += f"- **Current Engine**: `{checkpointer_type}`\n"
    md += f"- **Current Thread**: `{thread_id}`\n"
    md += f"- **Messages held in this thread**: **{len(history)} messages**\n\n"
    
    if checkpointer_type.startswith("Sqlite"):
        md += "✅ **Storage mode**: Persistent SQLite (`ci_conversations.sqlite`). If the server restarts or browser refreshes, these conversations are preserved.\n\n"
        md += f"**Discovered Threads in SQLite File ({len(all_sqlite_threads)}):**\n"
        for th in all_sqlite_threads:
            marker = "  *(Active)*" if th == thread_id else ""
            md += f"- `{th}`{marker}\n"
    else:
        md += "⚠️ **Storage mode**: In-Memory (`InMemorySaver`). High speed scratchpad, but all memory is wiped if the server process restarts.\n\n"

    if history:
        md += "\n**Raw History Preview for this thread:**\n"
        for i, m in enumerate(history[-4:], start=1):
            role_badge = "🧑 **Leader**" if m["role"] == "user" else "🤖 **CI Copilot**"
            snippet = m["content"][:140] + ("..." if len(m["content"]) > 140 else "")
            md += f"{i}. {role_badge}: {snippet}\n\n"
    return md


# Build the Gradio Application
with gr.Blocks(title="CI Value Stream AI Copilot") as demo:
    gr.Markdown(
        """
        # ⚡ Continuous Improvement (CI) Value Stream AI Copilot
        ### *Operational Excellence Assistant Powered by LangChain, DeepSeek-Chat, and 6-Layer Memory Architecture*
        """
    )

    with gr.Accordion("🎯 How this App Implements All 6 Memory Concepts", open=False):
        gr.Markdown(
            """
            This application demonstrates how professional AI agents manage memory in complex enterprise domains:
            1. **Conversation History**: Multi-turn conversational continuity within the active Continuous Improvement thread.
            2. **Checkpointer with thread-id**: Toggle between **`SqliteSaver`** (persists to disk, survives server restarts) and **`InMemorySaver`** (ephemeral RAM). Threads never leak into each other!
            3. **Durable Memory**: The CI Leader's identity, belt level, value stream scope, and target KPIs persist across ALL threads in `ci_leader_profile.json`.
            4. **Semantic Memory**: Automatically queries an institutional knowledge base of 8 past Kaizen A3 cases using TF-IDF vector retrieval to benchmark solutions.
            5. **Procedural Memory (Skills)**: Six Lean Six Sigma playbooks (`VSM`, `5-Whys`, `Gemba Waste`, `DMAIC Charter`, `SMED`, `Poka-Yoke`). The model sees only the menu, then loads the winner (Progressive Disclosure).
            6. **Context Management**: Context Packet architecture with a sliding window (last 4 turns) + running executive summary to prevent context bloat and slash token usage by 50-75%!
            """
        )

    # Top Control Bar: Checkpointer & Thread ID
    with gr.Row():
        with gr.Column(scale=1):
            cp_selector = gr.Radio(
                choices=["SqliteSaver (Persistent on Disk)", "InMemorySaver (Volatile RAM)"],
                value="SqliteSaver (Persistent on Disk)",
                label="Checkpointer Backend (Concept 2)",
            )
        with gr.Column(scale=2):
            thread_picker = gr.Dropdown(
                choices=PRESET_THREADS,
                value=PRESET_THREADS[0],
                allow_custom_value=True,
                label="Active Project Thread ID (Isolates Context per Project)",
            )
        with gr.Column(scale=1):
            with gr.Row():
                clear_thread_btn = gr.Button("🗑️ Clear Thread", size="sm")
                reset_profile_btn = gr.Button("🔄 Reset Profile", size="sm")

    # Memory Toggle Switches
    with gr.Row():
        toggle_durable = gr.Checkbox(value=True, label="Durable Profile Memory (Concept 3)")
        toggle_semantic = gr.Checkbox(value=True, label="Semantic Kaizen Memory (Concept 4)")
        toggle_procedural = gr.Checkbox(value=True, label="Procedural Skills (Concept 5)")
        toggle_compression = gr.Checkbox(value=True, label="Context Compression (Concept 6)")

    # Main Chat and Telemetry Dashboard
    with gr.Row():
        # Left: Chatbot Area (Scale 3)
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                height=520,
                label="Continuous Improvement Value Stream Dialogue",
            )
            msg_input = gr.Textbox(
                placeholder="Ask about VSM calculations, SMED changeovers, 5-Whys, or introduce yourself...",
                label="Your Operational Query",
                lines=2,
            )
            with gr.Row():
                send_btn = gr.Button("🚀 Send Query", variant="primary", scale=2)
                clear_chat_btn = gr.Button("Clear Screen", scale=1)

            gr.Markdown("**Quick Scenarios to Test Each Memory Layer:**")
            with gr.Row():
                chip_profile = gr.Button(EXAMPLE_PROMPTS[0][0], size="sm")
                chip_vsm = gr.Button(EXAMPLE_PROMPTS[1][0], size="sm")
                chip_semantic = gr.Button(EXAMPLE_PROMPTS[2][0], size="sm")
                chip_5whys = gr.Button(EXAMPLE_PROMPTS[3][0], size="sm")
                chip_gemba = gr.Button(EXAMPLE_PROMPTS[4][0], size="sm")

        # Right: Memory Inspector Tabs (Scale 2)
        with gr.Column(scale=2):
            with gr.Tabs() as tabs:
                with gr.TabItem("📊 Live Context Packet"):
                    telemetry_panel = gr.Markdown(format_telemetry_markdown(None))

                with gr.TabItem("👤 Durable Profile"):
                    profile_panel = gr.Markdown(get_profile_markdown())
                    refresh_profile_btn = gr.Button("Refresh Profile View", size="sm")

                with gr.TabItem("🧠 Semantic Knowledge Base"):
                    gr.Markdown("### Institutional Kaizen A3 Repository\n*Semantic Memory searches these past projects:*")
                    semantic_search_box = gr.Textbox(placeholder="Search Kaizen repository...", label="Test Semantic Query")
                    semantic_results_box = gr.Markdown()
                    
                    def run_kb_search(q):
                        if not q.strip():
                            cases = load_knowledge_base()
                            lines = [f"**Repository holds {len(cases)} verified Kaizen projects:**\n"]
                            for c in cases:
                                lines.append(f"- **[{c['id']}] {c['title']}** ({c['value_stream']})")
                            return "\n".join(lines)
                        results = search_semantic_memory(q, top_k=3, min_score=0.1)
                        if not results:
                            return "No matching cases found."
                        lines = [f"**Top Semantic Matches for '{q}':**\n"]
                        for r in results:
                            c = r["case"]
                            lines.append(f"#### [{c['id']}] {c['title']} (Score: {r['score']}%)")
                            lines.append(f"- **Problem**: {c['problem']}")
                            lines.append(f"- **Countermeasure**: {c['countermeasures']}")
                            lines.append(f"- **Results**: {c['results']}\n")
                        return "\n".join(lines)

                    semantic_search_box.change(run_kb_search, [semantic_search_box], [semantic_results_box])

                with gr.TabItem("🛠️ Procedural Skills (Playbooks)"):
                    gr.Markdown("### CI Standard Work Playbooks (`ci_skills/`)\n*Loaded via Progressive Disclosure:*")
                    skill_names = [s["name"] for s in ci_skills]
                    skill_dropdown = gr.Dropdown(choices=skill_names, value=skill_names[0] if skill_names else None, label="Inspect Playbook")
                    skill_content = gr.Markdown()

                    def show_skill_body(name):
                        for s in ci_skills:
                            if s["name"] == name:
                                return f"**File**: `ci_skills/{s['file']}`\n\n**Trigger Description**:\n{s['description']}\n\n---\n\n{s['body']}"
                        return "Select a skill to inspect."

                    skill_dropdown.change(show_skill_body, [skill_dropdown], [skill_content])

                with gr.TabItem("💾 Checkpointer State"):
                    checkpointer_panel = gr.Markdown(get_checkpointer_status(PRESET_THREADS[0], "SqliteSaver"))
                    refresh_cp_btn = gr.Button("Refresh Checkpointer View", size="sm")

    # --- Interaction Logic ---
    def on_submit(
        message,
        history,
        thread_id,
        checkpointer_choice,
        use_dur,
        use_sem,
        use_proc,
        use_comp,
    ):
        if not message.strip():
            return "", history, gr.update(), gr.update(), gr.update()

        cp_type = "SqliteSaver" if "sqlite" in checkpointer_choice.lower() else "InMemorySaver"

        reply, tel = execute_ci_turn(
            message=message,
            thread_id=thread_id,
            checkpointer_type=cp_type,
            use_durable_memory=use_dur,
            use_semantic_memory=use_sem,
            use_procedural_memory=use_proc,
            use_context_compression=use_comp,
        )

        history = history or []
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": reply})

        tel_md = format_telemetry_markdown(tel)
        prof_md = get_profile_markdown()
        cp_md = get_checkpointer_status(thread_id, cp_type)

        return "", history, tel_md, prof_md, cp_md

    # Wire up Send button and Enter key
    inputs = [
        msg_input,
        chatbot,
        thread_picker,
        cp_selector,
        toggle_durable,
        toggle_semantic,
        toggle_procedural,
        toggle_compression,
    ]
    outputs = [msg_input, chatbot, telemetry_panel, profile_panel, checkpointer_panel]

    send_btn.click(on_submit, inputs, outputs)
    msg_input.submit(on_submit, inputs, outputs)

    # Clear chat display (does not wipe memory)
    clear_chat_btn.click(lambda: [], None, chatbot)

    # Thread Switch handler
    def on_thread_change(thread_id, checkpointer_choice):
        cp_type = "SqliteSaver" if "sqlite" in checkpointer_choice.lower() else "InMemorySaver"
        saved_history = load_thread_history(thread_id, cp_type)
        cp_md = get_checkpointer_status(thread_id, cp_type)
        tel_md = f"### Switched to Thread `{thread_id}`\n\nLoaded **{len(saved_history)} messages** from {cp_type}."
        return saved_history, tel_md, cp_md

    thread_picker.change(on_thread_change, [thread_picker, cp_selector], [chatbot, telemetry_panel, checkpointer_panel])
    cp_selector.change(on_thread_change, [thread_picker, cp_selector], [chatbot, telemetry_panel, checkpointer_panel])

    # Clear Thread memory handler
    def on_clear_thread(thread_id, checkpointer_choice):
        reset_thread(thread_id)
        cp_type = "SqliteSaver" if "sqlite" in checkpointer_choice.lower() else "InMemorySaver"
        cp_md = get_checkpointer_status(thread_id, cp_type)
        return [], f"### Memory for Thread `{thread_id}` has been cleared.", cp_md

    clear_thread_btn.click(on_clear_thread, [thread_picker, cp_selector], [chatbot, telemetry_panel, checkpointer_panel])

    # Reset Profile handler
    def on_reset_profile():
        reset_profile()
        return get_profile_markdown(), "### Durable Profile Reset\nProfile has been cleared to empty defaults."

    reset_profile_btn.click(on_reset_profile, None, [profile_panel, telemetry_panel])

    # Refresh buttons
    refresh_profile_btn.click(get_profile_markdown, None, profile_panel)
    refresh_cp_btn.click(
        lambda th, cp: get_checkpointer_status(th, "SqliteSaver" if "sqlite" in cp.lower() else "InMemorySaver"),
        [thread_picker, cp_selector],
        checkpointer_panel,
    )

    # Example Prompt Chips
    chip_profile.click(lambda: EXAMPLE_PROMPTS[0][1], None, msg_input)
    chip_vsm.click(lambda: EXAMPLE_PROMPTS[1][1], None, msg_input)
    chip_semantic.click(lambda: EXAMPLE_PROMPTS[2][1], None, msg_input)
    chip_5whys.click(lambda: EXAMPLE_PROMPTS[3][1], None, msg_input)
    chip_gemba.click(lambda: EXAMPLE_PROMPTS[4][1], None, msg_input)

    # Initial view load
    demo.load(
        lambda: (
            get_profile_markdown(),
            run_kb_search(""),
            show_skill_body(skill_names[0] if skill_names else ""),
            get_checkpointer_status(PRESET_THREADS[0], "SqliteSaver")
        ),
        None,
        [profile_panel, semantic_results_box, skill_content, checkpointer_panel]
    )


if __name__ == "__main__":
    print("=" * 70)
    print("CONTINUOUS IMPROVEMENT VALUE STREAM AI COPILOT")
    print("Launching Gradio UI with all 6 Memory Architectures...")
    print("=" * 70)
    try:
        demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
    except OSError:
        print("[Notice] Port 7860 is currently in use by another process.")
        print("[Notice] Launching on next available port...")
        demo.launch(server_name="127.0.0.1", share=False)

