---
name: node-lookup
description: Automatically identify relevant Fusion Automation / n8n-style nodes from documentation files based on user automation intent. Suggest realistic workflows including node sequence and important configuration fields.
allowed-tools: find_file, read_file
---

# Node Lookup & Workflow Suggestion Skill

## When to activate

Use this skill for **every automation-related question**, especially when the user describes a task they want to automate, e.g.:

- "summarize my emails and send summary via WhatsApp"
- "post new RSS items to Twitter"
- "send daily weather report to Slack"
- "backup Google Drive folder to Dropbox every night"
- "extract data from PDF invoices and save to Airtable"

Do NOT activate for general questions or when user already names specific nodes/files.

## Core procedure

1. **Parse the user intent**
   - Identify main actions (summarize, send, fetch, post, backup, notify, …)
   - Identify data sources / triggers (email, RSS, new file, schedule, webhook, …)
   - Identify destinations / outputs (WhatsApp, Slack, Twitter, Airtable, email, …)
   - Identify processing needs (summarize, translate, filter, convert, …)

2. **Infer node filenames**
   - Triggers: Email Trigger (IMAP), Schedule Trigger, RSS Feed Trigger, Webhook, Chat Trigger, …
   - Sources: Gmail, Google Drive, RSS Read, Airtable, Notion, Google Sheets, …
   - Processing: OpenAI, Summarize, AI Transform, Filter, Code, Edit Fields, …
   - Destinations: WhatsApp Business Cloud, Slack, Telegram, Discord, Send Email, Twilio, …
   - Utilities: Merge, Switch, Wait, Loop Over Items, HTTP Request, …

   Common patterns:
   - email → gmail.md or Email*Trigger**IMAP**node*.json
   - summarize → OpenAI*node*.json or Summarize\_.json
   - whatsapp → WhatsApp*Business_Cloud_node*.json
   - twitter / x → X**Formerly_Twitter**node\_.json
   - schedule → Schedule*Trigger_node*.json

3. **Locate documentation**
   - Use find*file("<inferred_name>.md") or find_file("<inferred_name>\_node*.json")
   - If not found, try close variants (lowercase, without prefix/suffix)

4. **Build workflow suggestion**
   - Order nodes logically (trigger → fetch → process → output)
   - For each node mention:
     - Purpose in this workflow
     - Key configuration fields (from doc)
     - Expected input/output shape
   - Mention connections (which output goes to which input)
   - Add notes about credentials, rate limits, error handling if relevant

5. **If missing nodes**
   - State clearly which parts are missing
   - Suggest alternatives or HTTP Request fallback

## Output style (in final answer)

- Use markdown
- Show numbered workflow steps
- Bold node names
- List important settings in bullet points
- End with disclaimer: "This is a suggested workflow based on available node documentation. Test thoroughly."
