# Continuous Improvement (CI) Value Stream AI Copilot

An enterprise-grade AI Assistant designed for **Process Excellence & Continuous Improvement Value Stream Leaders**, built with **LangChain**, **DeepSeek-Chat (`deepseek-chat`)**, and **Gradio**.

This application brings together all 6 core memory architectures practiced in Mission 4 into a unified, interactive decision-support system.

---

## 🎯 Architecture Overview: The 6 Memory Systems in Action

| Memory Type | What it Represents in Process Excellence | How It Works Here | File / Location |
| :--- | :--- | :--- | :--- |
| **1. Conversation History** | Multi-turn conversational flow | Maintains active dialogue within the current turn and session | `app.py` & `gr.Chatbot` |
| **2. Checkpointer (`thread_id`)** | Segregation between different continuous improvement projects (e.g. VSM vs SMED vs DMAIC) | Switchable **`SqliteSaver`** (persists to disk, survives server restarts) vs **`InMemorySaver`** (ephemeral RAM). Threads never leak into each other. | `ci_conversations.sqlite` |
| **3. Durable Memory** | The CI Leader's identity, certification (Master Black Belt), plant scope, and baseline operational KPIs | Persists across ALL project threads and sessions. Facts mentioned in conversation are extracted via structured output and saved. | `ci_leader_profile.json` |
| **4. Semantic Memory** | Institutional memory of past Kaizen A3 events, standard work precedents, and historical root cause analyses | Searches an 8-case institutional Kaizen database using TF-IDF vector retrieval and injects relevant precedents. | `ci_knowledge_base.json` & `ci_semantic_memory.py` |
| **5. Procedural Memory** | Standard Operating Procedures (SOPs), 5-Whys guidelines, VSM formulas, SMED stages | Stored in markdown playbooks in `ci_skills/`. Progressive disclosure: model reads a tiny menu, picks the right playbook, and injects only that procedure. | `ci_skills/*.md` & `ci_skills_loader.py` |
| **6. Context Management** | Context Packet architecture to prevent token bloat during extended Kaizen events | Sliding window (last 4 turns verbatim) + Running Executive Kaizen Summary of older turns. Slashes token costs by 50% to 75%. | `ci_engine.py` (Telemetry inspector) |

---

## 🚀 How to Run

1. Open your terminal in this folder:
   ```bash
   cd "e:\Sridhar\Agentathon 6\mission4-Memory"
   ```
2. Ensure your `.env` contains your `DEEPSEEK_API_KEY`:
   ```bash
   DEEPSEEK_API_KEY=your_deepseek_api_key_here
   ```
3. Launch the application:
   ```bash
   uv run app.py
   ```
4. Open your browser at:
   ```
   http://127.0.0.1:7860
   ```

---

## 🧪 6-Step Guided Walkthrough (Test Each Memory Concept)

Use the quick-action buttons below the chatbox or copy-paste these prompts to observe how each memory system responds:

### Step 1: Test Durable Memory (Concept 3)
1. Select thread **`VSM-AutoInverter-Line1`**.
2. Click the **`👤 Durable Profile`** chip or send:
   > *"I am Sridhar, Lean Six Sigma Master Black Belt leading the Automotive Electronics value stream at Chennai Plant 2. Our target Takt is 45s and target PCE is 25%."*
3. **Observe**:
   - The agent addresses you as Sridhar, acknowledges your Master Black Belt role, and notes your targets.
   - Switch to the **👤 Durable Profile** tab on the right: see how `ci_leader_profile.json` captured all facts automatically!

### Step 2: Test Procedural Memory / Skills (Concept 5)
1. In the same thread, click the **`📐 VSM Calculation`** chip or send:
   > *"Analyze our VSM: Operating time is 450 mins/shift, customer demand is 480 units. Station cycle times: S1 Prep=32s, S2 Assembly=68s, S3 Inspection=40s, S4 Packaging=28s. What is our Takt and line constraint?"*
2. **Observe**:
   - In the **📊 Live Context Packet** tab: the model picked **Value Stream Mapping Analysis** (`ci_skills/vsm_analysis.md`).
   - The model computes Takt Time = $450 \times 60 / 480 = 56.25$ seconds, flags Station 2 ($68\text{ s} > 56.25\text{ s}$) as the bottleneck, and recommends specific Kaizen bursts.

### Step 3: Test Semantic Memory (Concept 4)
1. Click the **`🧠 Semantic Search`** chip or send:
   > *"We are suffering huge changeover downtime on our stamping press taking 85 minutes between tool setups. Have we solved this before?"*
2. **Observe**:
   - In the **📊 Live Context Packet** tab: Semantic memory automatically retrieved **Case KZ-2024-01: Stamping Press Die Changeover SMED Optimization** (similarity score > 50%).
   - The agent benchmarks the previous solution (pneumatic U-clamps, pre-staged dies) which achieved an 88.8% setup time reduction ($85\text{ min} \to 9.5\text{ min}$) and saved \$160,000!

### Step 4: Test Procedural Memory on 5-Whys RCA (Concept 5)
1. Click the **`🔍 5-Whys RCA`** chip or send:
   > *"Run a 5-Whys on yesterday's breakdown: CNC Milling Spindle stalled during heavy cut, error code E-402, 45 minutes of line downtime."*
2. **Observe**:
   - The model selects the **5-Whys Root Cause Analysis** playbook (`ci_skills/five_whys_rca.md`).
   - Also retrieves **Case KZ-2024-05** from Semantic Memory (hydraulic pressure cavitation).
   - Generates the unbroken 5-Whys chain with the "Therefore" backward test, root cause classification, and containment vs permanent countermeasures.

### Step 5: Test Checkpointer Isolation (`thread_id`) (Concept 2)
1. Change the Active Project Thread dropdown from `VSM-AutoInverter-Line1` to **`Kaizen-SMED-Press04`**.
2. Notice the chat clears and switches to the new thread.
3. Ask: *"What is my problem in this project?"*
   - Notice: The agent knows **nothing** about the VSM or CNC breakdown from the first thread! A different `thread_id` is a strictly isolated memory space.
4. Now ask: *"Who am I and what plant do I lead?"*
   - Notice: It immediately replies: **"You are Sridhar, Master Black Belt leading the Automotive Electronics value stream at Chennai Plant 2."**
   - **Why?** The thread changed, but the **Durable Profile** follows you into every thread!
5. Switch back to `VSM-AutoInverter-Line1`: Your full earlier conversation instantly returns!

### Step 6: Test Context Compression & Running Summary (Concept 6)
1. Continue chatting in any thread for 4 to 6 turns (e.g. asking about takt times, changeovers, safety metrics).
2. Look at the **📊 Live Context Packet** tab:
   - Once turns exceed the sliding window, older turns are folded into the **Running Executive Kaizen Summary**.
   - Review the **Token Optimization** gauge: see how it shows **50% to 75% tokens saved** compared to sending the full uncompressed chat history!

---

## 📂 Project Directory Structure

```text
mission4-Memory/
├── app.py                      # Main Gradio Application & UI Dashboard
├── ci_engine.py                # Core multi-tier memory orchestrator
├── ci_durable_memory.py        # Durable profile storage (Pydantic + JSON)
├── ci_semantic_memory.py       # Semantic retrieval engine (TF-IDF vector search)
├── ci_skills_loader.py         # Procedural playbooks loader & chooser
├── ci_knowledge_base.json      # 8 Real-world Kaizen A3 case studies
├── ci_leader_profile.json      # Persistent leader profile
├── ci_conversations.sqlite     # Persistent checkpointer database
├── ci_skills/                  # Procedural Memory Playbooks:
│   ├── vsm_analysis.md         # Value Stream Mapping & Takt Balancing
│   ├── five_whys_rca.md        # 5-Whys Root Cause Analysis
│   ├── gemba_waste_audit.md    # 8 Wastes (DOWNTIME) Gemba walk
│   ├── dmaic_project_charter.md# DMAIC Project Charter Builder
│   ├── smed_rapid_changeover.md# Single-Minute Exchange of Die (SMED)
│   └── fmea_poka_yoke.md       # Mistake-proofing & FMEA RPN
```

