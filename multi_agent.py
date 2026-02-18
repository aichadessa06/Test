import os
from pathlib import Path
from datetime import datetime
import sys
from contextlib import contextmanager

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, max_tokens=3000, timeout=90)

# ──── Root setup ────────────────────────────────────────────────────────
root_path = str(Path(".").resolve())
print("Backend root:", root_path)
print("Current dir:", os.getcwd())
print()

fs_backend = FilesystemBackend(root_dir=root_path, virtual_mode=True)

# ──── Directory tree preview  ─────────────
def print_directory_tree(startpath, max_depth=4):
    print("Directory structure (depth ≤", max_depth, "):")
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        if level > max_depth:
            continue
        indent = '  ' * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = '  ' * (level + 1)
        md_files = [f for f in sorted(files) if f.lower().endswith('.md')]
        for f in md_files[:8]:
            print(f"{sub_indent}• {f}")
        if len(md_files) > 8:
            print(f"{sub_indent}… (+{len(md_files)-8} more .md files)")
print_directory_tree(".", max_depth=4)
print("\n" + "─" * 70 + "\n")



# ──── Tools ─────────────────────────────────────────────────────────────
@tool
def find_file(filename: str) -> str:
    """Find a node description file (.md) by name. Returns relative path or 'Not found'."""
    for root, _, files in os.walk(root_path):
        if filename in files:
            p = Path(root) / filename
            return str(p.relative_to(root_path)).replace("\\", "/")
    return "Not found"

# ──── Writer sub-agent ──────────────────────────────────────
writer_agent = create_deep_agent(
    model=llm,
    backend=fs_backend,
    system_prompt="You are a privileged writer sub-agent. Execute filesystem write tasks concisely."
)

@tool
def delegate_write_task(task: str) -> str:
    """Delegate file write/edit/delete/rename tasks only when your reasoning truly requires it."""
    resp = writer_agent.invoke({"messages": [HumanMessage(content=task)]})
    return resp["messages"][-1].content

# ──── Main automation assistant ─────────────────────────────────────────
read_only_agent = create_deep_agent(
    model=llm,
    backend=fs_backend,
    tools=[delegate_write_task, find_file],
    skills=["skills/"],
    system_prompt="""You are a Fusion Automation Platform (n8n-style) workflow assistant.

Your job:
- Understand what the user wants to automate
- Use the 'node-lookup' skill to find relevant node documentation
- Propose a clear, realistic workflow (trigger → actions → processing → output)
- Include node names, sequence, and important configuration fields
- Be practical — mention credentials, common pitfalls, rate limits when relevant

Keep answers structured, use markdown, number the steps.
If important nodes are missing, say so honestly.
Never guess features that are not in the documentation.
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

def run_agent(query: str):
    print("\n" + "═"*85)
    print(f" QUERY:  {query}")
    print("═"*85 + "\n")

    with redirect_to_log():
        print(f"[START] {datetime.now().strftime('%H:%M:%S')}\n")
        events = read_only_agent.stream(
            {"messages": [HumanMessage(content=query)]},
            stream_mode=["messages", "updates"],
            subgraphs=True,
        )
        for event in events:
            # minimal logging — full trace goes to file
            pass

    # Clean final answer in terminal
    response = read_only_agent.invoke({"messages": [HumanMessage(content=query)]})
    final = response["messages"][-1].content

    print(" SUGGESTED WORKFLOW ")
    print("═"*85)
    print(final.strip())
    print()


if __name__ == "__main__":
    print("Test queries:\n")

    run_agent("I want to summarize my Gmail emails every morning and send the summary as a WhatsApp message to myself.")

    run_agent("Automate getting new RSS items from a blog and posting them to X (Twitter).")

    run_agent("Create a workflow that downloads new files from Google Drive folder and uploads them to Dropbox.")

    run_agent("Send me a daily weather forecast for Casablanca on Telegram.")


