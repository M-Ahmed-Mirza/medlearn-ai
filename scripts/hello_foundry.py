"""
MedLearn AI - Foundry Connectivity Smoke Test

Confirms we can:
1. Load credentials from .env
2. Connect to Microsoft Foundry
3. Call our gpt-4o deployment
4. Receive a response

Run from project root:
    python scripts/hello_foundry.py
"""

import os
import sys
from dotenv import load_dotenv

# Load .env from project root
load_dotenv()

# Read credentials from environment
ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
API_KEY = os.getenv("AZURE_AI_API_KEY")
DEPLOYMENT = os.getenv("AZURE_AI_MODEL_DEPLOYMENT")


def check_env_vars() -> None:
    """Verify all required environment variables are set."""
    missing = []
    if not ENDPOINT:
        missing.append("AZURE_AI_PROJECT_ENDPOINT")
    if not API_KEY:
        missing.append("AZURE_AI_API_KEY")
    if not DEPLOYMENT:
        missing.append("AZURE_AI_MODEL_DEPLOYMENT")

    if missing:
        print(f"ERROR: Missing required env vars: {', '.join(missing)}")
        print("Check your .env file and try again.")
        sys.exit(1)

    print("All required environment variables loaded.")
    print(f"  Endpoint: {ENDPOINT[:40]}...")
    print(f"  API Key:  {API_KEY[:8]}...{API_KEY[-4:]}")
    print(f"  Deployment: {DEPLOYMENT}")


def hello_foundry() -> None:
    """Make a single chat completion call to verify connectivity."""
    from openai import AzureOpenAI

    # Foundry's Azure OpenAI endpoint is derived from the project endpoint
    # The project endpoint URL needs minor adjustment for the OpenAI SDK
    aoai_endpoint = ENDPOINT.replace("/api/projects/medlearn-ai-foundry", "")

    print(f"\nConnecting to Foundry...")

    client = AzureOpenAI(
        api_key=API_KEY,
        api_version="2024-10-21",
        azure_endpoint=aoai_endpoint,
    )

    print("Client created. Sending test prompt...")

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": "You are MedLearn AI, a multi-agent system for healthcare workforce certification. Respond briefly and clearly.",
            },
            {
                "role": "user",
                "content": "Hello! Confirm you are responding through Microsoft Foundry by telling me your model name in one short sentence.",
            },
        ],
        max_tokens=80,
        temperature=0.3,
    )

    answer = response.choices[0].message.content
    usage = response.usage

    print("\n" + "=" * 60)
    print("FOUNDRY RESPONSE")
    print("=" * 60)
    print(answer)
    print("=" * 60)
    print(f"\nTokens used: input={usage.prompt_tokens}, output={usage.completion_tokens}, total={usage.total_tokens}")
    print("\nPhase 2A complete. MedLearn AI can talk to Foundry.")


if __name__ == "__main__":
    check_env_vars()
    hello_foundry()