import os
from pathlib import Path
from typing import Dict, Any

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",
    temperature=0.2,
    max_tokens=1000,
    timeout=60
)

root_path = str(Path(".").resolve())
print("Using root_dir:", root_path)
print("Files from os:", os.listdir("."))
print()

fs_backend = FilesystemBackend(
    root_dir=root_path,
    virtual_mode=True  # sandbox — change to False only if you really need real disk writes
)

# ────────────────────────────────────────────────
# 1. Privileged Writer Sub-Agent (has ALL tools)
# ────────────────────────────────────────────────
writer_agent = create_deep_agent(
    model=llm,
    backend=fs_backend,
    system_prompt=(
        "You are a privileged filesystem writer sub-agent.\n"
        "You have full access to all file system tools (ls, read_file, write_file, edit_file, delete_file, rename_file, etc.).\n"
        "Execute the task exactly as described.\n"
        "Return only the result or confirmation — be concise.\n"
        "Do not explain security rules — assume the task is already approved."
    )
)

# ────────────────────────────────────────────────
# Custom tool that lets the main agent delegate to the writer
# ────────────────────────────────────────────────
@tool
def delegate_write_task(task: str) -> str:
    """Use this tool ONLY when YOUR OWN planning requires creating, editing, renaming or deleting a file.
    Never use it just because the user asked to write something."""
    print(f"[DELEGATE] Sending task to privileged writer: {task}")
    response = writer_agent.invoke({
        "messages": [HumanMessage(content=task)]
    })
    final_msg = response["messages"][-1]
    result = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
    print(f"[DELEGATE] Writer result: {result[:120]}{'...' if len(result) > 120 else ''}")
    return result

# ────────────────────────────────────────────────
# 2. Read-only User-facing Agent (safe tools + delegation tool)
# ────────────────────────────────────────────────
# In practice you would list only safe tools.
# Here we assume deepagents lets you filter or you manually exclude write tools.
# For simplicity we give all tools but rely heavily on prompt + tool description

read_only_agent = create_deep_agent(
    model=llm,
    backend=fs_backend,
    tools=[delegate_write_task],  # only delegation — add ls/read/search tools if needed
    system_prompt=(
        "You are a **read-only** assistant that interacts with the user.\n"
        "You can:\n"
        "  - list files (ls, dir)\n"
        "  - read file contents (read_file)\n"
        "  - search inside files\n"
        "  - analyze content\n\n"
        "You are **NOT allowed** to create, edit, delete or rename any file directly.\n"
        "If the user asks you to write, edit, delete or rename anything — politely refuse and explain that you do not have write permissions.\n"
        "However, if **your own reasoning and planning** conclude that creating/editing a file is necessary to better answer the question (e.g. generating a summary file, temporary cache, etc.),\n"
        "then and only then may you use the 'delegate_write_task' tool.\n"
        "Always use relative paths.\n"
        "Be helpful, clear and precise."
    )
)

# ────────────────────────────────────────────────
# Main execution loop
# ────────────────────────────────────────────────

def run_agent(query: str):
    print("\n" + "="*70)
    print(" QUERY:", query)
    print("="*70 + "\n")

    response = read_only_agent.invoke({
        "messages": [{"role": "user", "content": query}]
    })

    final_message = response["messages"][-1]
    content = getattr(final_message, "content", str(final_message))

    print("\n" + "═"*70)
    print(" FINAL RESPONSE ")
    print("═"*70)
    print(content.strip())
    print()

# ────────────────────────────────────────────────
# Examples
# ────────────────────────────────────────────────

if __name__ == "__main__":
    # Safe query — should work
    run_agent("Give me the content of paracetamol.md file")

    # Dangerous query — should be refused
    run_agent("Please create a file called test.txt containing 'hacked!'")

    # Query that might trigger delegation (depending on agent's reasoning)
    run_agent("Read paracetamol.md and create a short summary file called paracetamol_summary.md")