"""
ci_durable_memory.py - Durable profile and organizational memory for Continuous Improvement Value Stream Leaders.

DURABLE MEMORY CONCEPT:
Thread memory belongs to ONE project thread (e.g., ticket-101 or project-alpha).
DURABLE MEMORY belongs to the PERSON and their VALUE STREAM.
It persists across all project threads, sessions, and system restarts.
When a Continuous Improvement Leader mentions their name, role, belt level, value stream scope,
or target metrics, the agent extracts these facts and updates ci_leader_profile.json.
Every subsequent conversation thread automatically inherits this identity.
"""

import json
import os
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model

PROFILE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ci_leader_profile.json")

PROFILE_FIELDS = [
    "leader_name",
    "role_title",
    "belt_level",
    "value_stream",
    "facility_location",
    "target_takt_time",
    "target_pce",
    "primary_methodology",
    "communication_preference",
]


class CILeaderProfile(BaseModel):
    """Structured facts extracted from the CI Value Stream Leader's dialogue."""
    leader_name: str = Field(default="", description="The leader's name if stated (e.g. Sridhar).")
    role_title: str = Field(default="", description="Their role or title (e.g. Value Stream Leader, CI Director).")
    belt_level: str = Field(default="", description="Their Lean/Six Sigma certification (e.g. Master Black Belt, Black Belt, Lean Champion).")
    value_stream: str = Field(default="", description="The value stream or product line they lead (e.g. Automotive Inverter Assembly, Precision Valve Machining).")
    facility_location: str = Field(default="", description="Plant, site, or facility location (e.g. Chennai Plant 2, Austin Facility).")
    target_takt_time: str = Field(default="", description="Target or operating Takt Time (e.g. 45s, 60 seconds).")
    target_pce: str = Field(default="", description="Target Process Cycle Efficiency or flow target (e.g. >25%, 30%).")
    primary_methodology: str = Field(default="", description="Preferred operational framework (e.g. Toyota Production System, DMAIC, Shingo Model).")
    communication_preference: str = Field(default="", description="Communication or reporting preference (e.g. concise tables, executive summary, 5-Whys focus).")


def load_profile():
    """Load the persistent profile from disk, or return empty default structure."""
    profile = {field: "" for field in PROFILE_FIELDS}
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for field in PROFILE_FIELDS:
                profile[field] = saved.get(field, "")
        except Exception:
            pass
    return profile


def save_profile(profile):
    """Save the profile dictionary to disk."""
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)


def extract_new_facts(message, model=None):
    """
    Use DeepSeek with structured output to extract profile facts from the leader's message.
    Returns only non-empty fields that were clearly stated.
    """
    if model is None:
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY")
        kwargs = {"temperature": 0.0, "max_tokens": 200}
        if api_key:
            kwargs["api_key"] = api_key
        model = init_chat_model("deepseek:deepseek-chat", **kwargs)

    extractor = model.with_structured_output(CILeaderProfile)
    try:
        result = extractor.invoke([
            {
                "role": "system",
                "content": (
                    "You extract operational facts about the Continuous Improvement Value Stream Leader from their message. "
                    "Only populate fields clearly and unambiguously stated by the user. "
                    "Leave all other fields as empty strings. Never guess or hallucinate."
                )
            },
            {"role": "user", "content": message}
        ])
        found = {}
        if result is None:
            return found
        for field in PROFILE_FIELDS:
            val = getattr(result, field, "").strip()
            if val:
                found[field] = val
        return found
    except Exception as e:
        return {}


def update_profile(message, model=None):
    """
    Extract facts from message, merge into durable profile file, and return updated profile + new facts.
    """
    new_facts = extract_new_facts(message, model=model)
    profile = load_profile()
    for k, v in new_facts.items():
        profile[k] = v
    if new_facts:
        save_profile(profile)
    return profile, new_facts


def profile_as_prompt_text(profile):
    """Format the durable profile for injection into the system prompt."""
    lines = []
    labels = {
        "leader_name": "CI Leader Name",
        "role_title": "Role & Responsibilities",
        "belt_level": "Certification Level",
        "value_stream": "Assigned Value Stream",
        "facility_location": "Operating Facility",
        "target_takt_time": "Target Takt Time",
        "target_pce": "Target Process Cycle Efficiency (PCE)",
        "primary_methodology": "Operational Excellence Methodology",
        "communication_preference": "Reporting & Style Preference",
    }
    for field in PROFILE_FIELDS:
        val = profile.get(field, "")
        if val:
            lines.append(f"- {labels.get(field, field)}: {val}")
    if not lines:
        return ""
    return "\nDurable Profile (CI Value Stream Leader Context):\n" + "\n".join(lines) + "\n"

