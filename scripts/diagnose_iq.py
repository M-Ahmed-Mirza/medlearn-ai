"""
MedLearn AI - Foundry IQ Request Diagnostic

Tries several documented request-body shapes against the knowledge base
retrieve endpoint and prints the FULL error body for each, so we can see
exactly what the preview API expects.

Run from project root:
    python -m scripts.diagnose_iq
"""

from dotenv import load_dotenv

load_dotenv()

import json
import os

import requests

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "").rstrip("/")
api_key = os.getenv("AZURE_SEARCH_API_KEY", "")
kb = os.getenv("AZURE_SEARCH_KNOWLEDGE_BASE", "medlearn-kb")

API_VERSIONS = ["2025-11-01-preview", "2026-04-01"]

# Candidate request bodies (different documented shapes)
BODIES = {
    "messages_typed": {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "burnout risk thresholds"}]}
        ]
    },
    "messages_plain": {
        "messages": [{"role": "user", "content": "burnout risk thresholds"}]
    },
    "knowledgeSourceParams_intents": {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "burnout risk thresholds"}]}
        ],
        "knowledgeSourceParams": [],
    },
    "query_only": {"query": "burnout risk thresholds"},
}

headers = {"Content-Type": "application/json", "api-key": api_key}

print("=" * 78)
print("Foundry IQ Request Diagnostic")
print("=" * 78)
print(f"Endpoint: {endpoint}\nKB: {kb}\n")

for api_version in API_VERSIONS:
    url = f"{endpoint}/knowledgebases/{kb}/retrieve?api-version={api_version}"
    print(f"\n########## API VERSION: {api_version} ##########")
    for name, body in BODIES.items():
        try:
            r = requests.post(url, json=body, headers=headers, timeout=30)
            print(f"\n[{name}] -> HTTP {r.status_code}")
            if r.status_code == 200:
                print("   SUCCESS ✅  Response keys:", list(r.json().keys()))
                print("   Full response (first 1500 chars):")
                print("   " + json.dumps(r.json(), indent=2)[:1500])
            else:
                # Print the error body — this tells us what's wrong
                try:
                    err = r.json()
                    print("   Error body:", json.dumps(err, indent=2)[:800])
                except Exception:
                    print("   Error text:", r.text[:800])
        except Exception as exc:
            print(f"\n[{name}] -> EXCEPTION: {type(exc).__name__}: {exc}")

print("\n" + "=" * 78)
print("Diagnostic complete. Look for the body shape that returned HTTP 200.")
print("=" * 78)
