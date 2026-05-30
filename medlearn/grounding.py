"""
MedLearn AI - Grounding Helper

Loads synthetic .md grounding documents from data/docs/ and packages them
as context for agents. This is a simple, local implementation.

PHASE 4 MIGRATION NOTE:
This module will be swapped out for Foundry IQ retrieval in Phase 4.
The agent-facing API (load_grounding_context, GroundingContext) will
stay the same — only the internal source changes. No agent code rewrite.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

# Project root = parent of agents/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "data" / "docs"


@dataclass
class GroundingContext:
    """Container for grounding documents passed to agents.

    documents: filename -> full text content
    """

    documents: Dict[str, str] = field(default_factory=dict)

    def as_prompt_block(self) -> str:
        """Format all loaded docs as a single block to inject into a prompt."""
        if not self.documents:
            return "(No grounding documents loaded.)"

        blocks = []
        for filename, content in self.documents.items():
            blocks.append(f"=== SOURCE: {filename} ===\n{content}\n=== END SOURCE ===\n")
        return "\n".join(blocks)

    def available_sources(self) -> List[str]:
        """List of filenames currently loaded."""
        return sorted(self.documents.keys())


def load_grounding_context(filenames: List[str] | None = None) -> GroundingContext:
    """Load grounding docs from data/docs/.

    Args:
        filenames: Specific filenames to load. If None, loads all .md files
                   in data/docs/.

    Returns:
        GroundingContext with the requested docs loaded.

    Raises:
        FileNotFoundError: if data/docs/ doesn't exist or a requested file is missing.
    """
    if not DOCS_DIR.exists():
        raise FileNotFoundError(
            f"Grounding docs directory not found: {DOCS_DIR}. "
            f"Expected data/docs/ at project root."
        )

    if filenames is None:
        # Load every .md file in data/docs/
        files_to_load = sorted(DOCS_DIR.glob("*.md"))
    else:
        files_to_load = [DOCS_DIR / name for name in filenames]
        for path in files_to_load:
            if not path.exists():
                raise FileNotFoundError(f"Grounding doc not found: {path}")

    context = GroundingContext()
    for path in files_to_load:
        context.documents[path.name] = path.read_text(encoding="utf-8")

    return context
