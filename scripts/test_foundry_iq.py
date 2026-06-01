"""
MedLearn AI - Foundry IQ Connectivity Test

Verifies that grounding_iq.py can retrieve real content from the Foundry IQ
knowledge base. Runs with safe=False so failures surface loudly (instead of
silently falling back to local docs).

Run from project root:
    python -m scripts.test_foundry_iq

Requires in .env:
    AZURE_SEARCH_ENDPOINT
    AZURE_SEARCH_API_KEY
    AZURE_SEARCH_KNOWLEDGE_BASE   (default: medlearn-kb)
"""

from dotenv import load_dotenv

load_dotenv()

import os

from medlearn.grounding_iq import load_grounding_context_iq


def main() -> int:
    print("=" * 78)
    print("MedLearn AI - Foundry IQ Connectivity Test")
    print("=" * 78)

    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    kb = os.getenv("AZURE_SEARCH_KNOWLEDGE_BASE", "medlearn-kb")
    print(f"  Endpoint: {endpoint}")
    print(f"  Knowledge base: {kb}")
    print(f"  API key set: {bool(os.getenv('AZURE_SEARCH_API_KEY'))}")
    print()

    queries = [
        "What are the burnout risk thresholds for study scheduling?",
        "What are the recommended study hours for CCRN certification?",
    ]

    for q in queries:
        print(f">> QUERY: {q}")
        try:
            ctx = load_grounding_context_iq(query=q, safe=False)
        except Exception as exc:
            print(f"   FAILED: {type(exc).__name__}: {exc}")
            print("\n  Foundry IQ retrieval did NOT succeed. See error above.")
            return 1

        sources = ctx.available_sources()
        block = ctx.as_prompt_block()
        print(f"   Retrieved {len(sources)} grounding section(s), "
              f"{len(block)} chars total.")
        # Show a short preview of the first section
        preview = block[:400].replace("\n", " ")
        print(f"   Preview: {preview}...")
        print()

    print("=" * 78)
    print("Foundry IQ connectivity test PASSED — retrieval returned content.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
