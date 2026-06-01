"""
MedLearn AI - Foundry IQ Grounding (Phase 4)

Retrieves grounding context from a Foundry IQ knowledge base (Azure AI Search
agentic retrieval) instead of reading local .md files. Returns the EXACT same
GroundingContext object that medlearn/grounding.py returns, so no agent code
changes.

Design:
    - Queries the knowledge base's `retrieve` action over REST
      (api-version 2025-11-01-preview), authenticated with the search admin
      API key (Free-tier friendly; no managed identity required).
    - Parses the extractive grounding chunks from the response defensively
      (the preview response shape varies), and packs them into a
      GroundingContext keyed by source reference.
    - On ANY failure (network, auth, empty result), the caller can fall back
      to local-docs grounding. This module never raises into agent code if
      `safe=True`.

Environment variables (in .env):
    AZURE_SEARCH_ENDPOINT      e.g. https://medlearn-ai.search.windows.net
    AZURE_SEARCH_API_KEY       primary admin key of the search service
    AZURE_SEARCH_KNOWLEDGE_BASE  e.g. medlearn-kb
    USE_FOUNDRY_IQ             "true" to enable IQ; anything else uses local docs

The agent-facing surface (GroundingContext, load_grounding_context) is
identical to medlearn/grounding.py. The orchestrator/agents import via
medlearn.grounding_router, which picks IQ or local based on USE_FOUNDRY_IQ.
"""

from __future__ import annotations

import os
from typing import List, Optional

import json

import requests

# Reuse the SAME GroundingContext dataclass the agents already depend on.
from medlearn.grounding import GroundingContext, load_grounding_context

API_VERSION = "2025-11-01-preview"
DEFAULT_TIMEOUT_S = 30

# A broad query that pulls the clinical/workload/compliance grounding.
# Minimal reasoning effort returns extractive chunks across the KB; we use a
# representative query that surfaces the policy content agents rely on.
_DEFAULT_QUERY = (
    "clinical certification requirements, study hour recommendations, "
    "burnout risk thresholds, workload correlations, and renewal planning windows"
)


def _kb_retrieve_url(endpoint: str, kb_name: str) -> str:
    endpoint = endpoint.rstrip("/")
    return f"{endpoint}/knowledgebases/{kb_name}/retrieve?api-version={API_VERSION}"


def _coerce_text(raw: str) -> List[str]:
    """A content value may be clean text OR a JSON-stringified array of
    {ref_id, content} blocks (the preview retrieve API does the latter).
    Return a list of clean text strings, unwrapping the JSON when present.
    """
    s = raw.strip()
    if not s:
        return []
    # Looks like a JSON array/object? Try to parse and pull inner content.
    if s[0] in "[{":
        try:
            parsed = json.loads(s)
        except Exception:
            return [raw]  # not actually JSON; use as-is
        texts: List[str] = []
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    inner = item.get("content") or item.get("text")
                    if isinstance(inner, str) and inner.strip():
                        texts.append(inner)
                elif isinstance(item, str) and item.strip():
                    texts.append(item)
        elif isinstance(parsed, dict):
            inner = parsed.get("content") or parsed.get("text")
            if isinstance(inner, str) and inner.strip():
                texts.append(inner)
        return texts or [raw]
    return [raw]


def _extract_chunks(payload: dict) -> List[tuple[str, str]]:
    """Pull (source_ref, text) pairs out of a retrieve response, defensively.

    The 2025-11-01-preview response groups content under a few possible keys
    depending on output mode. We probe the documented shapes and degrade
    gracefully rather than assuming one structure. Content values that are
    JSON-stringified arrays of {ref_id, content} blocks are unwrapped to
    clean text.
    Returns a list of (reference, content) tuples.
    """
    chunks: List[tuple[str, str]] = []

    # Shape A: top-level "response" list of content blocks
    response_blocks = payload.get("response")
    if isinstance(response_blocks, list):
        for block in response_blocks:
            if isinstance(block, dict):
                content = block.get("content")
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("text"):
                            for t in _coerce_text(c["text"]):
                                chunks.append((str(c.get("ref_id", block.get("ref_id", "kb"))), t))
                elif isinstance(content, str) and content.strip():
                    for t in _coerce_text(content):
                        chunks.append((str(block.get("ref_id", "kb")), t))

    # Shape B: "references" array (grounding data with source ids)
    references = payload.get("references")
    if isinstance(references, list):
        for ref in references:
            if isinstance(ref, dict):
                text = ref.get("content") or ref.get("text") or ""
                source = (
                    ref.get("sourceData", {}).get("title")
                    if isinstance(ref.get("sourceData"), dict)
                    else None
                ) or ref.get("docKey") or ref.get("id") or "kb"
                if text and text.strip():
                    for t in _coerce_text(text):
                        chunks.append((str(source), t))

    # Shape C: simple "content" string at top level
    top_content = payload.get("content")
    if isinstance(top_content, str) and top_content.strip():
        for t in _coerce_text(top_content):
            chunks.append(("kb", t))

    return chunks


def load_grounding_context_iq(
    query: Optional[str] = None,
    safe: bool = True,
) -> GroundingContext:
    """Retrieve grounding from the Foundry IQ knowledge base.

    Args:
        query: Retrieval query. Defaults to a broad clinical/workload query.
        safe: If True (default), any failure falls back to local-docs
              grounding instead of raising. Set False to surface errors
              (useful for the connectivity test script).

    Returns:
        GroundingContext populated from KB chunks (or local docs on fallback).
    """
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    api_key = os.getenv("AZURE_SEARCH_API_KEY")
    kb_name = os.getenv("AZURE_SEARCH_KNOWLEDGE_BASE", "medlearn-kb")

    if not endpoint or not api_key:
        msg = "AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY must be set for Foundry IQ."
        if safe:
            return load_grounding_context()  # fall back to local docs
        raise RuntimeError(msg)

    url = _kb_retrieve_url(endpoint, kb_name)
    # Knowledge bases configured with 'minimal' reasoning effort require the
    # 'intents' input (the 'messages' input is only valid at low/medium effort,
    # where an LLM does query planning). See Azure AI Search retrieve API docs.
    body = {
        "intents": [
            {"type": "semantic", "search": query or _DEFAULT_QUERY}
        ]
    }
    headers = {"Content-Type": "application/json", "api-key": api_key}

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=DEFAULT_TIMEOUT_S)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:  # network / auth / parse
        if safe:
            return load_grounding_context()
        # Surface the server's error detail when available — it's diagnostic.
        detail = ""
        try:
            detail = f" | {resp.json().get('error', {}).get('message', '')}"
        except Exception:
            pass
        raise RuntimeError(f"Foundry IQ retrieve failed: {exc}{detail}") from exc

    chunks = _extract_chunks(payload)
    if not chunks:
        if safe:
            return load_grounding_context()
        raise RuntimeError(
            "Foundry IQ returned no grounding chunks; check KB content/config."
        )

    # Pack chunks into a GroundingContext. Group by source reference so the
    # as_prompt_block() output stays organized like the local-docs version.
    context = GroundingContext()
    for source_ref, text in chunks:
        key = f"foundry-iq::{source_ref}"
        if key in context.documents:
            context.documents[key] += "\n\n" + text
        else:
            context.documents[key] = text

    return context