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
    max_tokens=2000,  
    timeout=90
)

root_path = str(Path(".").resolve())
print("Using root_dir:", root_path)
print("Files from os:", os.listdir("."))
print()

fs_backend = FilesystemBackend(
    root_dir=root_path,
    virtual_mode=True
)

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
    )
)

@tool
def delegate_write_task(task: str) -> str:
    """Use ONLY when YOUR OWN planning requires creating, editing, renaming or deleting a file.
    Never use it just because the user asked to write something."""
    print(f"[WRITE DELEGATION] Task: {task[:80]}{'...' if len(task)>80 else ''}")
    response = writer_agent.invoke({"messages": [HumanMessage(content=task)]})
    final_msg = response["messages"][-1]
    result = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
    print(f"[WRITE RESULT] {result[:120]}{'...' if len(result)>120 else ''}")
    return result

# ────────────────────────────────────────────────
# Read-only User-facing Agent 
# ────────────────────────────────────────────────
read_only_agent = create_deep_agent(
    model=llm,
    backend=fs_backend,
    tools=[delegate_write_task],
    system_prompt=(
        "You are a **read-only medical & scientific knowledge assistant** with access to files in the current directory.\n"
        "You can:\n"
        "  - list files (ls, dir)\n"
        "  - read file contents (read_file)\n"
        "  - search inside files\n"
        "  - analyze and **combine information from multiple files**\n\n"
        "You are **NOT allowed** to create, edit, delete or rename any file directly.\n"
        "If the user asks to write, edit, delete or rename anything — politely refuse and explain that you do not have write permissions.\n"
        "However, if **your own reasoning** concludes that creating/editing a file would significantly improve the answer (e.g. generating a combined summary or interaction table),\n"
        "then you may use the 'delegate_write_task' tool with a clear, precise task description.\n\n"
        "Important rules for health/medical questions:\n"
        "  - When asked about combinations of substances (e.g. paracetamol + vitamin C), **read all relevant files** (e.g. paracetamol.md, vitaminC.md, etc.)\n"
        "  - Cross-reference information from multiple files\n"
        "  - Reason step-by-step about possible interactions, side effects, contraindications\n"
        "  - Be very cautious — if information is missing or contradictory, say so\n"
        "  - Always remind the user: 'This is not medical advice. Consult a doctor or pharmacist.'\n"
        "  - Use common scientific knowledge only when files do not provide enough information\n\n"
        "Always use relative paths. Be helpful, accurate, structured and clear."
    )
)

def run_agent(query: str):
    print("\n" + "═"*90)
    print(f" QUERY: {query}")
    print("═"*90 + "\n")

    # We now stream to show reasoning steps
    print("Agent thinking & tool usage:\n")
    response = read_only_agent.invoke({
        "messages": [{"role": "user", "content": query}]
    })

    final_message = response["messages"][-1]
    content = getattr(final_message, "content", str(final_message))

    print("\n" + "═"*90)
    print(" FINAL RESPONSE ")
    print("═"*90)
    print(content.strip())
    print()

if __name__ == "__main__":
    # Test cases
    run_agent("Give me the content of paracetamol.md file")

    run_agent("What are the main uses and dosage of paracetamol according to paracetamol.md?")

    # The kind of question we want the agent to handle well
    run_agent(
        "If I took paracetamol and vitamin C together, would there be any health consequences? "
        "Look in paracetamol.md and vitaminC.md and reason about possible interactions."
    )

    # Dangerous write request – should be refused
    run_agent("Please create a file called test.txt containing 'hacked!'")
