"""
ci_semantic_memory.py - Semantic memory retrieval for Continuous Improvement Value Stream Leaders.

SEMANTIC MEMORY CONCEPT:
Associative, long-term memory containing institutional knowledge, past Kaizen A3 events,
standard operating lessons learned, and historical problem-solving records.
When a user describes an operational problem, semantic retrieval finds the most relevant
precedent from organizational history and injects it into context as a benchmark.
"""

import json
import math
import os
import re

KB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ci_knowledge_base.json")


def tokenize(text):
    """Normalize text into lowercase alphanumeric tokens."""
    return re.findall(r"\b[a-z0-9]{2,}\b", text.lower())


def load_knowledge_base():
    """Load the historical Kaizen case repository."""
    if not os.path.exists(KB_FILE):
        return []
    with open(KB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_corpus_vocab(cases):
    """Compute document frequency (DF) for TF-IDF calculations."""
    doc_freq = {}
    N = len(cases)
    case_tokens = []
    for case in cases:
        combined = f"{case['title']} {case['problem']} {case['root_cause']} {case['countermeasures']} {case.get('keywords', '')}"
        tokens = set(tokenize(combined))
        case_tokens.append(tokens)
        for t in tokens:
            doc_freq[t] = doc_freq.get(t, 0) + 1
    return doc_freq, N, case_tokens


def search_semantic_memory(query, top_k=2, min_score=0.15):
    """
    Search the institutional Kaizen knowledge base using TF-IDF cosine similarity.
    Returns list of matched cases with similarity scores.
    """
    cases = load_knowledge_base()
    if not cases or not query.strip():
        return []

    doc_freq, N, case_tokens_list = build_corpus_vocab(cases)
    q_tokens = tokenize(query)
    if not q_tokens:
        return []

    q_weights = {}
    for t in q_tokens:
        df = doc_freq.get(t, 0)
        idf = math.log((N + 1) / (df + 1)) + 1.0
        q_weights[t] = q_weights.get(t, 0) + idf

    q_norm = math.sqrt(sum(w * w for w in q_weights.values()))
    if q_norm == 0:
        return []

    results = []
    for i, case in enumerate(cases):
        combined = f"{case['title']} {case['problem']} {case['root_cause']} {case['countermeasures']} {case.get('keywords', '')}"
        doc_tokens = tokenize(combined)
        tf_dict = {}
        for t in doc_tokens:
            tf_dict[t] = tf_dict.get(t, 0) + 1

        dot_product = 0.0
        doc_sq_sum = 0.0
        for t, count in tf_dict.items():
            df = doc_freq.get(t, 1)
            idf = math.log((N + 1) / (df + 1)) + 1.0
            weight = count * idf
            doc_sq_sum += weight * weight
            if t in q_weights:
                dot_product += q_weights[t] * weight

        doc_norm = math.sqrt(doc_sq_sum)
        score = (dot_product / (q_norm * doc_norm)) if (q_norm * doc_norm) > 0 else 0.0

        if score >= min_score:
            results.append({
                "case": case,
                "score": round(score * 100, 1)
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def format_semantic_context(matched_cases):
    """Format retrieved semantic memories into prompt-ready context text."""
    if not matched_cases:
        return ""

    lines = ["\nRelevant Historical Kaizen Precedents from Organizational Semantic Memory:"]
    for match in matched_cases:
        c = match["case"]
        lines.append(
            f"• Case {c['id']} - {c['title']} (Relevance: {match['score']}%)\n"
            f"  - Value Stream: {c['value_stream']}\n"
            f"  - Prior Issue & Root Cause: {c['problem']} | Root Cause: {c['root_cause']}\n"
            f"  - Proven Countermeasure: {c['countermeasures']}\n"
            f"  - Verified Benchmark Result: {c['results']}"
        )
    return "\n".join(lines) + "\n"

