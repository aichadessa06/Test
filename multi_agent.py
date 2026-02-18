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

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, max_tokens=2000, timeout=90)

# ──── Use current directory as root ─────────────────────────────────────
root_path = str(Path(".").resolve())
print("Backend root directory:", root_path)
print("Current working directory:", os.getcwd())
print()

fs_backend = FilesystemBackend(root_dir=root_path, virtual_mode=True)

# ──── Show directory structure at startup ───────────────────────────────
def print_directory_tree(startpath, max_depth=4):
    print("Directory structure (up to depth", max_depth, "):")
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        if level > max_depth:
            continue
        indent = '│   ' * (level - 1) + '├── ' if level > 0 else ''
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = '│   ' * level + '├── '
        for f in sorted(files)[:12]:
            print(f"{sub_indent}{f}")
        if len(files) > 12:
            print(f"{sub_indent}... (+{len(files)-12} more)")
        if level == max_depth:
            print(f"{'│   ' * level}└── ... (deeper folders omitted)")

print_directory_tree(".", max_depth=4)
print("\n" + "─" * 70 + "\n")


# ──── File finder tool (needed cuz skills give instructions, not implementation) ──
@tool
def find_file(filename: str) -> str:
    """Search for a file by name in the project directory and subdirectories.
    Returns the relative path if found, or 'File not found' if not."""
    for root, dirs, files in os.walk(root_path):
        if filename in files:
            full_path = Path(root) / filename
            rel_path = str(full_path.relative_to(root_path))
            return rel_path.replace("\\", "/")  # Normalize slashes
    return "File not found"

# ────────────────────────────────────────────────
# Privileged Writer Sub-Agent
# ────────────────────────────────────────────────
writer_agent = create_deep_agent(
    model=llm,
    backend=fs_backend,
    system_prompt=(
        "You are a privileged filesystem writer sub-agent.\n"
        "You have full access to all file system tools.\n"
        "Execute the task exactly as described.\n"
        "Return only the result or confirmation — be concise."
    ),
)

@tool
def delegate_write_task(task: str) -> str:
    """Use ONLY when YOUR OWN planning requires creating, editing, renaming or deleting a file."""
    response = writer_agent.invoke({"messages": [HumanMessage(content=task)]})
    final_msg = response["messages"][-1]
    result = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
    return result

# ────────────────────────────────────────────────
# Read-only User-facing Agent with SKILL support
# ────────────────────────────────────────────────
read_only_agent = create_deep_agent(
    model=llm,
    backend=fs_backend,
    tools=[delegate_write_task, find_file],           
    skills=["skills/"],                               # ← points to the skills/ folder
    system_prompt=(
        "You are a read-only assistant with access to files in the current directory and subdirectories.\n\n"
        "Capabilities:\n"
        "- Use the 'file-finder' skill when user asks for a file by name only\n"
        "- list files and folders (ls, dir, list_directory) — use sparingly\n"
        "- read file contents (read_file)\n"
        "- combine & analyze information from multiple files\n\n"
        "You are NOT allowed to create, edit, delete or rename files directly.\n"
        "If writing seems necessary, use 'delegate_write_task'.\n\n"
        "For medical questions: cross-reference files, be cautious, always add disclaimer.\n\n"
        "Be accurate, structured, and helpful. Use relative paths only."
    ),
)

# ──── Logging helper ────────────────────────────────────────

LOG_FILE = "agent_run.log"

@contextmanager
def redirect_stream_to_log():
    original_stdout = sys.stdout
    log_path = Path(LOG_FILE).resolve()

    with open(log_path, "a", encoding="utf-8") as log_f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_f.write(f"\n\n===== New agent run @ {timestamp} =====\n")
        log_f.write(f"Root: {root_path}\n")
        log_f.write("-" * 70 + "\n\n")

        class LogWriter:
            def write(self, text):
                log_f.write(text)
                log_f.flush()
            def flush(self):
                log_f.flush()

        sys.stdout = LogWriter()
        try:
            yield
        finally:
            sys.stdout = original_stdout
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("-" * 70 + "\n")

def run_agent(query: str):
    print("\n" + "═" * 80)
    print(f" QUERY →  {query}")
    print("═" * 80 + "\n")

    with redirect_stream_to_log():
        print(f"[START] {datetime.now().strftime('%H:%M:%S')}\n")
        events = read_only_agent.stream(
            {"messages": [HumanMessage(content=query)]},
            stream_mode=["messages", "updates"],
            subgraphs=True,
        )

        chunk_count = 0
        for event in events:
            chunk_count += 1
            try:
                if len(event) == 3:
                    namespace, mode, chunk = event
                elif len(event) == 2:
                    mode, chunk = event
                    namespace = None
                else:
                    print(f"Unexpected event: {event}")
                    continue

                if mode == "messages":
                    last = chunk[-1] if isinstance(chunk, list) else chunk
                    content = getattr(last, "content", str(last))
                    if content.strip():
                        prefix = f"[{namespace or 'main'}] " if namespace else ""
                        print(f"{prefix}{mode}: {content[:600]}{'…' if len(content)>600 else ''}")
                elif mode == "updates":
                    print(f"[{namespace or 'main'}] update → {str(chunk)[:300]}")
            except Exception as e:
                print(f"Chunk {chunk_count} error: {e}")

        print(f"\n[END] {datetime.now().strftime('%H:%M:%S')}  (chunks: {chunk_count})\n")

    # Final clean answer
    response = read_only_agent.invoke({"messages": [HumanMessage(content=query)]})
    final_msg = response["messages"][-1]
    final_content = getattr(final_msg, "content", str(final_msg))

    print("═" * 80)
    print(" FINAL ANSWER ")
    print("═" * 80)
    print(final_content.strip())
    print()


if __name__ == "__main__":
    print("Running test queries...\n")
    run_agent("Give me the full content of agent.md")
    run_agent("What does agent.md say about how agents are created or configured?")
    #run_agent("Please create a file called test.txt containing 'hello from agent'")
    run_agent("Give me the  content of akhbarona.md")

    run_agent("Based on NODE_DESCRIPTIONS.md , I want an automation that summaries all emails and send the summary via whatsapp, give me the nodes I need in this workflow")
    run_agent("Based on NODE_DESCRIPTIONS.md , I want an automation that summaries all emails from gmail and send the summary via whatsapp message, give me the exact nodes I need in this workflow (for each node give me its relative file)")

