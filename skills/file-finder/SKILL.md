---
name: file-finder
description: Use this skill whenever the user asks about a specific file by name (e.g. agent.md, paracetamol.md) without providing a full path. This skill ensures efficient location and reading of documentation files scattered in subfolders without wasting tokens on repeated directory listings.
allowed-tools: find_file, read_file
---

# File Finder Skill

## When to use this skill
Activate this skill automatically when:
- The user mentions a .md, .txt, .json, .py or similar file name without a full relative path
- Questions like "what does X.md say", "read agent.md", "show content of Y.md", etc.

DO NOT guess paths or use list_directory multiple times — that consumes unnecessary resources.

## Step-by-step procedure
1. Immediately call the `find_file` tool with the exact filename mentioned by the user.
   - Input: just the basename (e.g. "agent.md", not a path)
   - It returns either:
     - a relative path (use it directly)
     - or "File not found"

2. If a path is returned:
   - Use `read_file` with that exact relative path
   - Include the path in your reasoning so it's visible in logs
   - Proceed to answer based on the content

3. If "File not found":
   - Politely tell the user you could not locate the file
   - Suggest providing more context or the approximate location
   - Do NOT fall back to blind list_directory walks

## Important notes
- `find_file` searches from the project root and returns the **first** match
- Always prefer this skill over manual path guessing
- This skill is especially useful for documentation files in deep folders like test/docs/cp-test/docs/nodes/en/ai/
