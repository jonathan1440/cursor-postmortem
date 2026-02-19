# Prompt Tracking for CLAUDE.md (or .cursor/rules)

**Goal:** Track every prompt you send in Cursor, analyze patterns, and use that to decide what to put in a central doc (CLAUDE.md or `.cursor/rules`) so you stop re-explaining the same things.

This is the “documentation based on data, not vibes” approach: the AI doesn’t maintain a memory store; *you* see what you keep asking and add that context to the project so the AI has it by default.

## How it works

1. **Log every prompt** – A Cursor **beforeSubmitPrompt** hook runs when you hit send. It appends a one-line JSON record to `.cursor/prompt-log.jsonl` (timestamp, conversation id, prompt text, first line, length, attachment count). Submission is never blocked.

2. **Analyze the log** – Run the analyzer script when you want to see patterns:
   ```bash
   python3 scripts/analyze-prompts.py
   ```
   It reports:
   - Total prompts and how many had attachments
   - Most frequent “first lines” (recurring intents)
   - **Suggested sections for CLAUDE.md**: headings derived from repeated first lines, with placeholders so you can fill in the actual context.

3. **Edit CLAUDE.md (or .cursor/rules)** – Add the suggested sections and write 1–2 sentences each (stack, convention, or decision). Next time you ask something in that area, the AI already has the context.

## What’s in this repo

| Item | Purpose |
|------|--------|
| `.cursor/hooks.json` | Registers **beforeSubmitPrompt** → `log-prompt.sh` |
| `.cursor/hooks/log-prompt.sh` | Reads prompt + metadata from stdin, appends one JSON line to `.cursor/prompt-log.jsonl`, returns `{"continue": true}` |
| `scripts/analyze-prompts.py` | Reads the log, prints summary + suggested CLAUDE.md sections |
| `.gitignore` (add line) | Add `.cursor/prompt-log.jsonl` so prompts aren’t committed |

## Setup

1. **Hooks are already configured** in this repo (`.cursor/hooks.json`). When you open this project in Cursor, the hook runs from the project root.

2. **Optional:** Add to `.gitignore`:
   ```
   .cursor/prompt-log.jsonl
   ```

3. **Run the analyzer** from the project root after you’ve sent some prompts:
   ```bash
   python3 scripts/analyze-prompts.py
   python3 scripts/analyze-prompts.py --suggest-only   # only suggested doc sections
   ```

## Log format (jsonl)

Each line is a JSON object:

- `ts` – ISO-ish timestamp
- `conversation_id` – Cursor conversation id
- `prompt` – full prompt text
- `first_line` – first line of prompt (trimmed, up to 200 chars), used for pattern detection
- `prompt_length` – character count
- `attachment_count` – number of file/rule attachments
- `attachment_types` – e.g. `"file,rule"`

You can point the analyzer at a different file with `--log path/to/log.jsonl`.

## Relation to the article

The article’s idea: you don’t know what to put in CLAUDE.md; the AI “tells you” what it needed. Here we use **your own prompts** as the signal: what you keep asking is what’s missing from the doc. No AI memory store, no MCP—just capture prompts and analyze them to drive documentation.

If you later want to add the article’s “47 lines of bash” style (e.g. auto-append a summary to a session file or run a weekly “suggest CLAUDE.md” job), you can wire the same log into that.
