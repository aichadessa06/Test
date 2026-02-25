import os
import json
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
    model="gpt-4.1-mini",  
    temperature=0.3,
    max_tokens=512,
    timeout=60,
    max_retries=5
)

# ──── Root setup ────────────────────────────────────────────────────────
root_path = str(Path(".").resolve())
print("Backend root:", root_path)
print("Current dir:", os.getcwd())
print()

fs_backend = FilesystemBackend(root_dir=root_path, virtual_mode=True)

# ──── Restricted docs root ──────────────────────────────────────────────
DOCS_ROOT = Path(root_path) / "test" / "docs" / "cp-test" / "docs" / "nodes"

# ──── Tools (restricted to docs folder) ─────────────────────────────────
@tool
def find_file(filename: str) -> str:
    """Find a node description file (.md) ONLY inside the docs/nodes folders."""
    for root, _, files in os.walk(DOCS_ROOT):
        if filename in files:
            p = Path(root) / filename
            return str(p.relative_to(root_path)).replace("\\", "/")
    return "Not found (searched only in docs/nodes)"

@tool
def list_directory(path: str) -> str:
    """List files/subfolders ONLY inside the docs/nodes folders."""
    full = DOCS_ROOT / path
    if not full.is_dir():
        return f"Directory not found or outside allowed scope: {path}"
    items = []
    for item in sorted(full.iterdir()):
        if item.is_dir():
            items.append(f"[DIR]  {item.name}")
        else:
            items.append(f"[FILE] {item.name}")
    return "\n".join(items) or "Empty directory"

# ──── Writer sub-agent ──────────────────────────────────────────────────
writer_agent = create_deep_agent(
    model=llm,
    backend=fs_backend,
    system_prompt="You are a privileged writer sub-agent. Execute filesystem write tasks concisely."
)

@tool
def delegate_write_task(task: str) -> str:
    """Delegate file write/edit/delete/rename tasks only when reasoning truly requires it."""
    resp = writer_agent.invoke({"messages": [HumanMessage(content=task)]})
    return resp["messages"][-1].content

# ──── Main read-only automation assistant ───────────────────────────────
read_only_agent = create_deep_agent(
    model=llm,
    backend=fs_backend,
    tools=[delegate_write_task, find_file, list_directory],
    skills=["skills/"],
    system_prompt="""You are a Fusion Automation Platform (n8n-style) assistant.

STRICT RULES:
- NEVER invent node names, filenames, parameters, models, defaults or connections.
- ONLY use information that actually exists in .md files you read.
- ONLY search inside test/docs/cp-test/docs/nodes/ folders (en/fr subfolders).
- For summarization, generation, reasoning → ONLY use nodes from ai/ folders that start with ai-chat-, chat-, llm-.
- When multiple nodes match → ALWAYS:
  - list all matching files with filename + short description
  - ask clearly: "Multiple options found. Please reply with the number (1, 2, ...) or the full filename you want to use."
- After user chooses → read the file → show the EXACT parameters table/list from the file.
- Ask ONE parameter at a time, clearly, e.g.:
  "Please enter the value for 'apiKey':"
  "What model do you want to use? Reply with the model name from the list."
- When all config is collected or user says "ok", "confirm", "generate", "done", "build", "finished", "save", "yes", "proceed":
  → output ONLY the JSON array — no extra text.
- JSON structure (simplified):

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
        "parameters": { ... exact keys from file + user values ... }
      }
    ],
    "connections": [
      "<source node name> → <target node name>",
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

def run_conversation(initial_query: str):
    messages = [HumanMessage(content=initial_query)]

    print("Starting agent...\n")
    print("Waiting for agent to respond... (may take 10–90 seconds)\n")

    while True:
        try:
            with redirect_to_log():
                print("[Processing...]")

                last_content = ""
                is_json = False
                waiting_for_input = False

                for event in read_only_agent.stream(
                    {"messages": messages},
                    config={
                        "max_tokens": 512,
                        "temperature": 0.3,
                        "max_retries": 5
                    },
                    stream_mode=[ "updates"],
                    subgraphs=True
                ):
                    if len(event) == 3:
                        namespace, mode, chunk = event
                    elif len(event) == 2:
                        mode, chunk = event
                        namespace = None
                    else:
                        print(f"⚠️  Unexpected event structure: {event}")
                        continue
                    if mode == "updates":
                        # Pass the original event for pretty printing
                        if namespace is not None:
                            pretty_print_messages((namespace, chunk))
                        else:
                            pretty_print_messages(chunk)
        except Exception as e:
            print(f"\nAgent error: {str(e)}")
            if "rate limit" in str(e).lower() or "429" in str(e):
                print("Rate limit — waiting 120 seconds...")
                time.sleep(120)
            elif "access denied" in str(e).lower() or "accès refusé" in str(e).lower():
                print("Access denied — skipping restricted path.")
            else:
                print("Unexpected error — check agent_run.log")
                break

        # Prompt only when needed
        if is_json:
            reply = input("\n(Workflow complete. Press Enter to continue or 'exit'): ").strip()
        elif waiting_for_input:
            reply = input("\n→ Your reply (or 'exit'/'quit'): ").strip()
        else:
            reply = ""  # silent wait

        if reply.lower() in ('exit', 'quit'):
            print("Goodbye!")
            break

        if reply:
            messages.append(HumanMessage(content=reply))

if __name__ == "__main__":
    initial = "I want to summarize my Gmail emails every morning and send the summary as a WhatsApp message to myself."
    run_conversation(initial)



