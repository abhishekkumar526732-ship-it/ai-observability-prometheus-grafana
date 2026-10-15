"""Local LangSmith Testing & Diagnostic Script.

Usage:
    python scripts/test_langsmith.py [--mock] [--query "Your question here"]

This script:
1. Validates your environment configuration (.env).
2. Verifies Groq and LangSmith credentials.
3. Tests connection to the LangSmith API.
4. Executes a traced request through LLMService or a local mock.
5. Displays token counts, response latency, and the LangSmith project trace link.
"""

import argparse
import asyncio
import os
import sys
import time
import uuid

# Ensure backend and qa-chatbot directories are in sys.path and .env is loaded
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
QA_CHATBOT_DIR = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(QA_CHATBOT_DIR, "backend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv

# Preload .env from qa-chatbot root directory
env_path = os.path.join(QA_CHATBOT_DIR, ".env")
if os.path.isfile(env_path):
    load_dotenv(env_path, override=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app.config import get_settings, setup_langsmith_tracing
from app.services.llm_service import LLMService


def print_banner() -> None:
    print("=" * 72)
    print("       [*] Q&A CHATBOT - LANGSMITH LOCAL TESTING & DIAGNOSTIC        ")
    print("=" * 72)


def print_config_table(settings) -> None:
    print("\n[+] Current Configuration:")
    print(f"  * Environment:             {settings.APP_ENV}")
    print(f"  * Groq Model:              {settings.GROQ_MODEL}")
    print(f"  * Groq API Key:            {settings.masked_groq_api_key} ({'[OK] READY' if settings.is_api_key_configured else '[X] NOT SET'})")
    print(f"  * LangSmith Tracing:       {'[OK] ENABLED' if settings.LANGSMITH_TRACING else '[X] DISABLED (LANGSMITH_TRACING=false)'}")
    print(f"  * LangSmith API Key:       {settings.masked_langsmith_api_key} ({'[OK] READY' if settings.is_langsmith_configured else '[!] UNCONFIGURED'})")
    print(f"  * LangSmith Project:       {settings.LANGSMITH_PROJECT}")
    print(f"  * LangSmith Endpoint:      {settings.LANGSMITH_ENDPOINT}")
    print("-" * 72)


async def test_langsmith_connection(settings) -> bool:
    """Verify connectivity with the LangSmith Cloud API."""
    print("\n[+] Step 1: Testing LangSmith Cloud API Connectivity...")
    try:
        from langsmith import Client
        client = Client(
            api_key=settings.LANGSMITH_API_KEY,
            api_url=settings.LANGSMITH_ENDPOINT,
            timeout_ms=5000,
        )
        try:
            has_proj = client.has_project(settings.LANGSMITH_PROJECT)
            if not has_proj:
                print(f"  [i] Project '{settings.LANGSMITH_PROJECT}' not found in LangSmith. Creating it now...")
                client.create_project(settings.LANGSMITH_PROJECT, description="Local development and testing for Q&A Chatbot")
            print(f"  [OK] Connection to LangSmith successful! Project: '{settings.LANGSMITH_PROJECT}'")
            return True
        except Exception as exc:
            err_str = str(exc)
            if "401" in err_str or "unauthorized" in err_str.lower():
                print("  [X] Authentication failed (HTTP 401). Verify your LANGSMITH_API_KEY in .env.")
                return False
            print(f"  [!] Note: Client checked with message: {exc}")
            return True
    except Exception as exc:
        print(f"  [X] Error connecting to LangSmith: {exc}")
        return False


async def run_traced_live_query(settings, query: str) -> None:
    """Execute a real query via ChatGroq with LangSmith tracing."""
    print("\n[+] Step 2: Executing Traced LLM Invocation...")
    print(f"  * Prompt: \"{query}\"")

    service = LLMService(settings=settings)
    session_id = str(uuid.uuid4())

    t0 = time.perf_counter()
    try:
        result = await service.generate_response(
            session_id=session_id,
            user_message=query,
        )
        duration = (time.perf_counter() - t0) * 1000.0

        print(f"\n[OK] AI Response Received ({duration:.1f} ms):")
        print("=" * 72)
        print(result.answer)
        print("=" * 72)
        print(f"  * Model:        {result.model}")
        print(f"  * Latency:      {result.latency_ms:.2f} ms")
        print(f"  * Token Usage:  {result.token_usage or 'N/A'}")
        print(f"  * Session ID:   {session_id}")

        print("\n[+] LangSmith Observability Status:")
        print(f"  * Traces logged to Project: '{settings.LANGSMITH_PROJECT}'")
        print("  * View traces in your browser at:")
        print("    --> https://smith.langchain.com/")
        print("=" * 72)

    except Exception as exc:
        print(f"  [X] LLM Generation Failed: {exc}")


async def run_offline_mock_test(settings, query: str) -> None:
    """Execute a mock traced function without requiring live external tokens."""
    print("\n[+] Running Offline / Mock Trace Simulation...")
    from langsmith import traceable

    @traceable(name="mock_qa_pipeline", run_type="chain", tags=["local-test", "mock"])
    async def simulated_llm_turn(prompt: str) -> dict:
        await asyncio.sleep(0.3)
        return {
            "answer": f"Simulated response to: '{prompt}'. LangChain & LangSmith pipeline hooks are active!",
            "tokens": {"prompt_tokens": 12, "completion_tokens": 18, "total_tokens": 30},
        }

    res = await simulated_llm_turn(query)
    print(f"  [OK] Simulated response: {res['answer']}")
    print(f"  * Simulated tokens: {res['tokens']}")
    print("  [OK] Traceable pipeline executed smoothly without exceptions!")


def print_setup_guide() -> None:
    print("\n[!] HOW TO ENABLE LANGSMITH TRACING FOR LOCAL TESTING:")
    print("1. Go to https://smith.langchain.com and sign up or log in (free tier available).")
    print("2. Navigate to Settings -> API Keys (https://smith.langchain.com/settings).")
    print("3. Click 'Create API Key', name it (e.g. 'local-testing'), and copy the key ('lsv2_pt_...').")
    print("4. Open your 'qa-chatbot/.env' file and configure:")
    print("      LANGSMITH_TRACING=true")
    print("      LANGSMITH_API_KEY=lsv2_pt_your_actual_key_here")
    print("      LANGSMITH_PROJECT=qa-chatbot-local")
    print("5. Re-run this script:")
    print("      python scripts/test_langsmith.py\n")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test LangSmith tracing locally for Q&A Chatbot")
    parser.add_argument("--mock", action="store_true", help="Run local simulation without calling Groq API")
    parser.add_argument("--query", type=str, default="Explain in 1 sentence what an API is.", help="User query to test")
    args = parser.parse_args()

    print_banner()
    settings = get_settings()
    print_config_table(settings)

    if args.mock:
        await run_offline_mock_test(settings, args.query)
        return

    if not settings.is_langsmith_configured:
        print("[!] LangSmith is not fully configured (missing valid LANGSMITH_API_KEY).")
        print_setup_guide()
        print("Running mock local trace verification instead...")
        await run_offline_mock_test(settings, args.query)
        return

    # If configured, test connectivity
    connected = await test_langsmith_connection(settings)
    if connected:
        if settings.is_api_key_configured:
            await run_traced_live_query(settings, args.query)
        else:
            print("[!] GROQ_API_KEY is not configured. Running offline trace simulation.")
            await run_offline_mock_test(settings, args.query)
    else:
        print_setup_guide()


if __name__ == "__main__":
    asyncio.run(main())
