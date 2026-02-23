import os
from pathlib import Path
from datetime import datetime
import sys
from contextlib import contextmanager
import uuid

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, max_tokens=3000, timeout=90)

# ──── Root setup ────────────────────────────────────────────────────────
root_path = str(Path(".").resolve())
print("Backend root:", root_path)
print("Current dir:", os.getcwd())
print()

fs_backend = FilesystemBackend(root_dir=root_path, virtual_mode=True)

# ──── Directory tree preview ─────────────
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
 """Find a node description file (.md or .json) by name. Returns relative path or 'Not found'."""
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

# ──── Checkpointer for HITL ─────────────────────────────────────────────
checkpointer = MemorySaver()

# ──── Main automation assistant with HITL ───────────────────────────────
read_only_agent = create_deep_agent(
 model=llm,
 backend=fs_backend,
 tools=[delegate_write_task, find_file],
 skills=["skills/"],
 checkpointer=checkpointer,
 interrupt_on={
     "find_file": True,
     "delegate_write_task": True,
 },  # Interrupt before these tools for human approval
 system_prompt="""You are a Fusion Automation Platform (n8n-style) workflow assistant.

    Strict rules:
    - For summarization, text analysis, generation or any intelligent processing → you MUST use a real LLM node from the ai/ folders (files starting with ai-chat- or chat-).
    - You are NOT allowed to suggest "Summarize Node", "AI Transform", generic "Function" or "Code" nodes for LLM tasks.
    - When you select an LLM node:
    1. Tell the user which node you chose and why
    2. Show the configuration table with all important parameters
    3. Ask interactively:
    - Which model they want (list the models you found in the node doc)
    - Their API key (required)
    - Optional: temperature, system prompt, max tokens, etc.
    - Be very detailed in the workflow description
    - Use clear markdown formatting

    After collecting config, you can confirm the final workflow.
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
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Start with the user's first message
    messages = [HumanMessage(content=initial_query)]

    print("Starting conversation. Type 'exit' to stop.\n")

    while True:
        # Stream events (reasoning stays in log)
        with redirect_to_log():
            print(f"[THREAD {thread_id[:8]}] Processing...")

            events = read_only_agent.stream(
                {"messages": messages},
                config=config,
                stream_mode=["values", "updates"]
            )

            for event in events:
                if "messages" in event:
                    last_msg = event["messages"][-1]
                    if isinstance(last_msg, AIMessage) and last_msg.content:
                        print(last_msg.content)

        # Check current state
        current_state = read_only_agent.get_state(config)

        if current_state.next:  # there is a node waiting (often interrupt)
            # Interrupt happened → human in the loop
            print("\n" + "═" * 60)
            print("AGENT IS WAITING FOR YOUR INPUT")
            print("Current pending actions / questions:")
            print(current_state.metadata.get("interrupt_reason", "Configuration needed"))

            user_reply = input("\nYour reply (or 'approve', 'reject', 'skip', 'exit'): ").strip()

            if user_reply.lower() in ("exit", "quit"):
                print("Conversation ended.")
                break

            # Resume with user input as new HumanMessage
            messages.append(HumanMessage(content=user_reply))


        else:
            # No interrupt → conversation naturally ended or waiting for next input
            last_ai_msg = current_state.values["messages"][-1]
            print("\n" + "═" * 60)
            print("FINAL / CURRENT RESPONSE")
            print(last_ai_msg.content.strip())
            print("═" * 60 + "\n")

            user_next = input("Your next message (or 'exit'): ").strip()
            if user_next.lower() in ("exit", "quit"):
                break
            messages.append(HumanMessage(content=user_next))


if __name__ == "__main__":
 print("Starting conversational agent...\n")
 initial_query = "I want to summarize my Gmail emails every morning and send the summary as a WhatsApp message to myself."
 run_conversation(initial_query)

