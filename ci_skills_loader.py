"""
ci_skills_loader.py - Procedural memory loader and selector for CI playbooks.

PROCEDURAL MEMORY CONCEPT:
Facts describe WHAT IS TRUE.
Procedural memory describes HOW TO EXECUTE STANDARD WORK.
In Lean Six Sigma, Standard Operating Procedures (SOPs), 5-Whys protocols, VSM calculation
formulas, and DMAIC phase gates are procedural memory.
Rather than stuffing all playbooks into the prompt (which wastes context and causes confusion),
we present a lightweight menu (names + descriptions), the model picks the relevant procedure,
and only that procedure is progressively disclosed.
"""

import os
from langchain.chat_models import init_chat_model

SKILLS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ci_skills")


def read_skill(path):
    """Read one markdown playbook and parse name, description, and procedure body."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    name = ""
    description = ""
    body_lines = []
    header_done = False

    for line in lines:
        if not header_done and line.lower().startswith("name:"):
            name = line.split(":", 1)[1].strip()
        elif not header_done and line.lower().startswith("description:"):
            description = line.split(":", 1)[1].strip()
        elif not header_done and line.strip() == "" and name and description:
            header_done = True
        else:
            if header_done:
                body_lines.append(line)

    return {
        "name": name,
        "description": description,
        "body": "".join(body_lines).strip(),
        "file": os.path.basename(path),
    }


def load_skills():
    """Load all CI markdown playbooks in the ci_skills folder."""
    skills = []
    if not os.path.exists(SKILLS_FOLDER):
        return skills
    for fname in sorted(os.listdir(SKILLS_FOLDER)):
        if fname.endswith(".md"):
            skills.append(read_skill(os.path.join(SKILLS_FOLDER, fname)))
    return skills


def find_skill(skills, name):
    """Find a skill by exact or partial name match."""
    wanted = name.strip().lower()
    for s in skills:
        if s["name"].lower() == wanted:
            return s
    for s in skills:
        if wanted in s["name"].lower():
            return s
    return None


def choose_skill(model, skills, message):
    """
    Display only the small menu to the model and select the best procedure.
    Uses progressive disclosure to preserve context window.
    """
    if not skills:
        return None

    menu = ""
    for s in skills:
        menu += f"- {s['name']}: {s['description']}\n"

    system_prompt = (
        "You are an expert Lean Six Sigma workflow coordinator. "
        "Select which operational playbook / procedural standard best matches the user's message.\n"
        "Playbook candidates (Name: Trigger description):\n\n"
        f"{menu}\n"
        "Reply ONLY with the exact NAME of the matching playbook. "
        "If none of them match the user's message, reply strictly with: NONE"
    )

    try:
        reply = model.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ])
        picked = reply.content.strip()
        if picked.upper().startswith("NONE"):
            return None
        return find_skill(skills, picked)
    except Exception:
        return None

