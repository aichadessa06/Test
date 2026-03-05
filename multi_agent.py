import os
import json
import re
from pathlib import Path
from datetime import datetime
import sys
from contextlib import contextmanager
import time

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from dotenv import load_dotenv
from print_messages import pretty_print_messages  

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.25,
    max_tokens=1200,
    timeout=90,
    max_retries=4
)

# ──── Root setup ────────────────────────────────────────────────────────
root_path = str(Path(".").resolve())
print("Backend root:", root_path)
print("Current dir:", os.getcwd())
print()

fs_backend = FilesystemBackend(root_dir=root_path, virtual_mode=True)

DOCS_ROOT_REL = "test/docs/cp-test/docs/nodes"
DOCS_ROOT = Path(root_path) / DOCS_ROOT_REL

# ──── Writer sub-agent ──────────────────────────────────────────────────
writer_agent = create_deep_agent(
    model=llm,
    backend=fs_backend,
    system_prompt="You are a privileged writer sub-agent. Execute filesystem write tasks concisely and safely."
)

@tool
def delegate_write_task(task: str) -> str:
    """Delegate file write/edit/delete/rename tasks only when truly necessary."""
    resp = writer_agent.invoke({"messages": [HumanMessage(content=task)]})
    return resp["messages"][-1].content if "messages" in resp and resp["messages"] else str(resp)

# ──── Custom helper: global file search by name ─────────────────────────
@tool
def find_file(filename: str) -> str:
    """Find a .md node description file anywhere under docs/nodes."""
    for root, _, files in os.walk(DOCS_ROOT):
        if filename in files:
            p = Path(root) / filename
            return str(p.relative_to(root_path)).replace("\\", "/")
    return f"Not found: {filename} (searched in {DOCS_ROOT_REL}/**/*.md)"

# ──── Main read-only agent ──────────────────────────────────────────────
read_only_agent = create_deep_agent(
    model=llm,
    backend=fs_backend,
    tools=[delegate_write_task, find_file],
    skills=["skills/"],
    system_prompt="""You are a Fusion Automation Platform (n8n-style) assistant.

MANDATORY RULES:

1. Use the built-in filesystem tools: ls, read_file, write_file, etc.
   → Explore with: ls test/docs/cp-test/docs/nodes/
   → Example: ls test/docs/cp-test/docs/nodes/en/ai

2. NEVER call invented tools like glob, search, os.walk, find_files — only use ls, read_file, find_file, delegate_write_task, etc.

3. NEVER invent node names, filenames, parameters, models or connections.
   ONLY use data from .md files you actually read.

4. For summarization / generation / reasoning tasks → only use files in ai/ folders starting with:
   ai-chat-*.md   chat-*.md   llm-*.md

5. When multiple matching nodes exist:
   - List filename + short description
   - Then write exactly:
     MULTIPLE_OPTIONS_FOUND
     Please reply with the number (1,2,...) or the full filename.

6. When asking for one parameter, end your message with:
   PARAMETER_NEEDED: parameter_name

7. When everything is ready → output ONLY valid JSON — no extra text.
   Structure:

[
  {
    "name": "<short workflow name>",
    "variables": {},
    "secrets": { ... },
    "nodes": [
      {
        "type": "<trigger/integration/ai/utility>",
        "name": "<filename without .md>",
        "label": "<node label from file>",
        "file": "<relative path>",
        "parameters": { ... exact keys + user values ... }
      }
    ],
    "connections": [
      "source_node → target_node",
      ...
    ]
  }
]
"""
)

# ──── Logging redirection ───────────────────────────────────────────────
LOG_FILE = "agent_run.log"

@contextmanager
def redirect_to_log():
    orig = sys.stdout
    log_path = Path(LOG_FILE).resolve()
    with open(log_path, "a", encoding="utf-8") as lf:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lf.write(f"\n\n===== Run @ {ts} =====\n")
        class LogOnly:
            def write(self, t): lf.write(t); lf.flush()
            def flush(self): lf.flush()
        sys.stdout = LogOnly()
        try:
            yield
        finally:
            sys.stdout = orig
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("-"*70 + "\n")

# ──── Main conversation loop ────────────────────────────────────────────
def run_conversation(initial_query: str):
    messages = [HumanMessage(content=initial_query)]
    print("Starting agent...\n")
    print("Waiting for agent to respond... (may take 10–90 seconds)\n")

    while True:
        try:
            with redirect_to_log():
                print("[Processing...]")

                last_content = ""
                for event in read_only_agent.stream(
                    {"messages": messages},
                    config={
                        "max_tokens": 1200,
                        "temperature": 0.25,
                        "max_retries": 4
                    },
                    stream_mode=["updates"],
                    subgraphs=True
                ):
                    # ── Robust event shape handling ─────────────────────
                    if isinstance(event, dict):
                        updates = event.get("updates", {})
                    elif isinstance(event, tuple) and len(event) > 0 and isinstance(event[-1], dict):
                        updates = event[-1].get("updates", {})
                    elif isinstance(event, tuple) and len(event) == 2 and isinstance(event[1], dict):
                        updates = event[1].get("updates", {})
                    else:
                        continue

                    if "messages" in updates:
                        for msg in updates["messages"]:
                            if isinstance(msg, AIMessage) and msg.content:
                                preview = msg.content[:280] + "…" if len(msg.content) > 280 else msg.content
                                print("AI →", preview)
                                last_content += msg.content + "\n"

                print("\n" + "="*70)

                # ── Human-in-the-loop logic ─────────────────────────────
                if "MULTIPLE_OPTIONS_FOUND" in last_content:
                    print("Agent found multiple options → please choose one")
                    reply = input("\n→ Your choice (number or filename) or 'exit': ").strip()

                elif match := re.search(r"PARAMETER_NEEDED:\s*([^\n]+)", last_content, re.IGNORECASE):
                    param = match.group(1).strip()
                    print(f"→ Agent is asking for: {param}")
                    reply = input(f"\nPlease enter value for '{param}': ").strip()

                elif last_content.strip().startswith("[") and last_content.strip().endswith("]"):
                    try:
                        json.loads(last_content)
                        print("\nWorkflow JSON ready!\n")
                        print(last_content)
                        reply = input("\nPress Enter to continue or type 'exit': ").strip()
                    except json.JSONDecodeError:
                        print("Agent output looks like JSON but failed to parse.")
                        reply = input("\n→ Your reply or 'exit': ").strip()

                else:
                    # Normal response
                    print("\nLast agent message:\n" + last_content.strip())
                    reply = input("\n→ Your reply (or 'exit'/'quit'): ").strip()

                if reply.lower() in ('exit', 'quit', 'q'):
                    print("Goodbye!")
                    break

                if reply:
                    messages.append(HumanMessage(content=reply))

        except Exception as e:
            print(f"\nAgent error: {str(e)}")
            if "rate limit" in str(e).lower() or "429" in str(e):
                print("Rate limit — waiting 120 seconds...")
                time.sleep(120)
            else:
                print("Unexpected error — check agent_run.log")
                break

if __name__ == "__main__":
    initial = "I want to summarize my Gmail emails every morning and send the summary as a WhatsApp message to myself."
    run_conversation(initial)

    
