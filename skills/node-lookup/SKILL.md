---
name: node-lookup
description: STRICTLY discover real nodes from the documentation folders. Never invent node names, parameters or connections. List real files when multiple choices exist and ask user to choose. Output ONLY the final JSON workflow when configuration is complete and user confirms.
allowed-tools: find_file, read_file, list_directory
---

# Node Lookup & Workflow Suggestion Skill – STRICT MODE

## Absolute rules – never break these

1. NEVER invent, guess, hallucinate or assume any node name, filename, model name, parameter name, default value or connection that is not explicitly present in a real .md file you have read.
2. ONLY use information that you have actually read from files using find_file or read_file.
3. ONLY look inside these folders (and their direct subfolders if any):
   - test/docs/cp-test/docs/nodes/en/ai/
   - test/docs/cp-test/docs/nodes/fr/ai/
   - test/docs/cp-test/docs/nodes/en/triggers/
   - test/docs/cp-test/docs/nodes/fr/triggers/
   - test/docs/cp-test/docs/nodes/en/integrations/
   - test/docs/cp-test/docs/nodes/fr/integrations/
   - test/docs/cp-test/docs/nodes/en/utilities/
   - test/docs/cp-test/docs/nodes/fr/utilities/
4. For summarization, generation, reasoning, classification, translation or any prompt-based / LLM task → ONLY consider files in the ai/ folders that start with ai-chat-, chat-, llm- or very similar prefix.
5. When multiple files/nodes could fulfill a role (e.g. several ai-chat-\*.md files), ALWAYS:
   - use list_directory on the relevant folder(s)
   - list all matching files with their filename and a short description (read from the file if needed)
   - ASK the user to choose one by replying with the filename or number
6. After the user chooses a node:
   - read the file again with read_file
   - copy the EXACT parameters table/list that is written in the file (do not add, remove or modify keys)
   - ask the user step-by-step for each REQUIRED parameter (especially apiKey, credentials, tokens)
7. NEVER write or modify files directly — only suggest via delegate_write_task if it is truly necessary for the answer.
8. ONLY output the final JSON workflow when:
   - user explicitly confirms ("ok", "confirm", "build", "generate", "done", "finished", "save", "yes", "proceed", etc.)
   - OR you have collected all necessary configuration values and the workflow is complete
9. When outputting JSON:
   - output ONLY the JSON array — no explanation, no markdown, no extra text before or after
   - use exactly this simplified structure (adapt values from the real conversation):

[
{
"name": "<short user-friendly name for the workflow>",
"variables": {},
"secrets": { ... only keys the user actually provided ... },
"nodes": [
{
"type": "<trigger / integration / ai / utility>",
"name": "<filename without .md>",
"label": "<node label / title from file>",
"file": "<full relative path to the .md>",
"parameters": { ... only keys that exist in the file + user-provided values ... }
}
// more real nodes in sequence
],
"connections": [
"<source node name> → <target node name>",
// simple directed strings
]
}
]

Do NOT include position, id, width, height, selected, dragHandle, sourceHandle, targetHandle or any other UI-specific fields.
