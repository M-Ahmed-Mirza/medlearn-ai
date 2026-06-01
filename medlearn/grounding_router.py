"""
MedLearn AI - Grounding Router

A thin selector that returns grounding context from EITHER the Foundry IQ
knowledge base OR the local .md docs, based on the USE_FOUNDRY_IQ env flag.

This keeps the local-docs path as a permanent, always-available fallback:
flip USE_FOUNDRY_IQ=false (or leave it unset) and the system behaves exactly
as it did before Foundry IQ existed. Flip it to true to ground via IQ.

The function signature matches medlearn.grounding.load_grounding_context so
callers can swap imports without any other change:

    from medlearn.grounding_router import load_grounding_context
"""

from __future__ import annotations

import os
from typing import List, Optional

from medlearn.grounding import GroundingContext
from medlearn.grounding import load_grounding_context as _load_local


def _iq_enabled() -> bool:
    return os.getenv("USE_FOUNDRY_IQ", "false").strip().lower() in {"1", "true", "yes", "on"}


def load_grounding_context(
    filenames: Optional[List[str]] = None,
) -> GroundingContext:
    """Return grounding context from Foundry IQ or local docs.

    - If USE_FOUNDRY_IQ is truthy: query the knowledge base (with automatic,
      safe fallback to local docs if anything goes wrong).
    - Otherwise: load local .md docs exactly as before.

    The `filenames` arg is honored only for the local path (IQ retrieves
    across the whole knowledge base).
    """
    if _iq_enabled():
        # Imported lazily so the IQ dependency (requests + env) is only needed
        # when the flag is on.
        from medlearn.grounding_iq import load_grounding_context_iq

        return load_grounding_context_iq(safe=True)

    return _load_local(filenames)
