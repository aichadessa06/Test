---
name: node-lookup
description: Automatically identify relevant Fusion Automation / n8n-style nodes from documentation files based on user automation intent. For summarization, generation, classification or any LLM task — strongly prefer nodes whose paths start with test/docs/cp-test/docs/nodes/*/ai/ai-chat-...
allowed-tools: find_file, read_file
---

# Node Lookup & Workflow Suggestion Skill

## Core rules for LLM tasks (summarization, generation, classification, extraction, reasoning, translation, etc.)

YOU **MUST**:

1. **Never** suggest generic "Code", "Function", "AI Transform" or "Summarize" nodes for LLM-powered steps.
2. **Only** use real LLM integration nodes whose files are located in one of these folders:
   - test/docs/cp-test/docs/nodes/en/ai/
   - test/docs/cp-test/docs/nodes/fr/ai/
3. Look **exclusively** for filenames that start with:
   - ai-chat-
   - chat-
   - llm-
     (examples: ai-chat-openai.md, ai-chat-anthropic.md, ai-chat-gemini.md, chat-completion.md, etc.)
4. If no such node is found → clearly state that no suitable LLM node was located and suggest fallback (HTTP Request to an API) — but do NOT invent one.

## Procedure when an LLM node is needed (e.g. summarization)

1. Use `find_file` with patterns like:
   - "ai-chat-\*.md"
   - "chat-\*.md"
   - full path prefix: "test/docs/cp-test/docs/nodes/en/ai/ai-chat-"

2. Once a suitable node is found (e.g. ai-chat-openai.md):
   - Read its content with read_file
   - Extract supported models, required/optional parameters, default values
   - Propose this node for the summarization step

3. Immediately switch to **interactive configuration mode**:
   - Show the list of **supported models** you found in the documentation of that node
   - Show a markdown table with all important configuration parameters (model, apiKey, temperature, systemMessage, maxTokens, topP, etc.)
   - Ask the user to choose:
     • which model they want (from the list you extracted)
     • their API key (required)
     • any other important settings they want to change (temperature, system prompt, max tokens, …)
   - Suggest good defaults for email summarization

4. Default system prompt suggestion for email summarization (you can show this as starting point):

## General workflow structure

Always propose the full sequence in detail, for example:

1. Trigger: Schedule (every morning)
2. Fetch emails: Gmail or Email Trigger (IMAP)
3. Summarize: [chosen ai-chat-xxx node] — with configuration table
4. Format (optional): Edit Fields / Markdown
5. Send: WhatsApp Business Cloud

Be very detailed: describe each node's purpose, key configs, inputs/outputs, connections.
End your response with questions to collect configuration values when needed.
