# Cursor Postmortem

Track every prompt you send in Cursor, analyze patterns, and use the results to fill in CLAUDE.md (or `.cursor/rules`) so you stop re-explaining the same things. Documentation driven by what you actually ask, not guesswork.

## How it works

1. **beforeSubmitPrompt** (Cursor [hooks](https://cursor.com/docs/agent/hooks)) runs when you hit send. A script reads the prompt and metadata, appends one JSON line to `.cursor/prompt-log.jsonl`, and always returns `continue: true` so the request is never blocked.
2. You run **`scripts/analyze-prompts.py`** when you want a report. It reads the log, finds repeated “first lines” (recurring intents), and prints a summary plus **suggested sections** for CLAUDE.md.
3. You add those sections to CLAUDE.md (or `.cursor/rules`) and fill in 1–2 sentences each. Future prompts in that area get the context automatically.

No AI memory store, no MCP—just logging and a local analyzer.

---

## How to use it

### Prerequisites

- **Cursor** with this project (or your project) open.
- **Python 3** for the analyzer.
- **jq** for the log script (used to read `workspace_roots` and build the log entry). Install with e.g. `brew install jq` (macOS) or your package manager.

### Global (user) setup — use in every project

You can run the hook from your **user Cursor config** so it applies to every project without copying files into each repo.

1. Create `~/.cursor/hooks.json` with:
   ```json
   {
     "version": 1,
     "hooks": {
       "beforeSubmitPrompt": [
         { "command": "./hooks/log-prompt.sh" }
       ]
     }
   }
   ```
   User hooks run from `~/.cursor/`, so the command is `./hooks/log-prompt.sh` (not `.cursor/hooks/...`).

2. Copy the log script into your home config:
   ```bash
   mkdir -p ~/.cursor/hooks
   cp /path/to/cursor-postmortem/.cursor/hooks/log-prompt.sh ~/.cursor/hooks/
   chmod +x ~/.cursor/hooks/log-prompt.sh
   ```

3. Restart Cursor. The hook runs for every project. The script uses **workspace_roots** from the hook payload, so logs are still written **per project** to `<project-root>/.cursor/prompt-log.jsonl`, not to a single global file.

4. Run the analyzer from whichever project you want to analyze (or use `--log` to point at a project’s log):
   ```bash
   cd /path/to/some-project
   python3 /path/to/cursor-postmortem/scripts/analyze-prompts.py
   ```

### In this repo

1. Open the `cursor-postmortem` project in Cursor. Hooks run automatically; no install step.
2. Use Cursor as usual (Agent, Composer, etc.). Every prompt is appended to `.cursor/prompt-log.jsonl` in this repo.
3. From the project root, run:
   ```bash
   python3 scripts/analyze-prompts.py
   ```
   You’ll see:
   - Total prompts, how many had attachments, average prompt length.
   - Most frequent first lines (things you ask repeatedly).
   - **Suggested additions for CLAUDE.md**: headings plus `<!-- Add 1–2 sentences -->` placeholders.
4. Create or edit `CLAUDE.md` (or a rule in `.cursor/rules/`) and add the suggested sections. Replace the placeholders with the real context (stack, convention, or decision). Re-run the analyzer anytime to get fresh suggestions.

### In a single other project (project-level hooks)

**Option A — install script (recommended)**

From this repo, run:

```bash
./scripts/install.sh /path/to/other-project
```

The script will:

- Copy `.cursor/hooks/log-prompt.sh` into the target and make it executable
- Create or merge `.cursor/hooks.json` so `beforeSubmitPrompt` runs that script (existing hooks are preserved)
- Add `.cursor/prompt-log.jsonl` to the target’s `.gitignore` if present
- Copy `scripts/analyze-prompts.py` into the target so you can run the analyzer from that project

Then open the target project in Cursor and use it as usual; run `python3 scripts/analyze-prompts.py` from the target’s root when you want suggestions.

**Option B — manual copy**

1. Copy into that project: `.cursor/hooks.json` (or add a `beforeSubmitPrompt` entry) and `.cursor/hooks/log-prompt.sh`; `chmod +x .cursor/hooks/log-prompt.sh`.
2. Copy `scripts/analyze-prompts.py` into that project, or run it from here with `--log /path/to/that/project/.cursor/prompt-log.jsonl`.
3. Open that project in Cursor; prompts log to that project’s `.cursor/prompt-log.jsonl`.

### Analyzer options

| Command | Effect |
|--------|--------|
| `python3 scripts/analyze-prompts.py` | Full report: summary stats, frequent first lines, then suggested CLAUDE.md sections. |
| `python3 scripts/analyze-prompts.py --suggest-only` | Only the suggested doc sections (no stats). |
| `python3 scripts/analyze-prompts.py --log path/to/log.jsonl` | Use a different log file (e.g. another project or a backup). |

Suggestions are based on **first-line frequency**: any first line that appears at least twice becomes a suggested heading. Fill in the body yourself.

### Log file

- **Location:** `<project-root>/.cursor/prompt-log.jsonl` (created automatically). With global hooks the script still writes to the active project’s `.cursor/` using `workspace_roots`. Add to `.gitignore` so prompts aren’t committed.
- **Format:** One JSON object per line: `ts`, `conversation_id`, `prompt`, `first_line`, `prompt_length`, `attachment_count`, `attachment_types`.

### Optional: sessionStart memory hook

This repo also includes a **sessionStart** hook that injects content from `.cursor/memory/store.json` into new sessions (for use with the separate memory MCP server). If you only want prompt tracking, you can remove the `sessionStart` entry from `.cursor/hooks.json`; the beforeSubmitPrompt hook will keep working. The sessionStart script requires `jq`.

---

## Files involved

| Path | Role |
|------|------|
| `.cursor/hooks.json` | Registers beforeSubmitPrompt (and optionally sessionStart). |
| `.cursor/hooks/log-prompt.sh` | Logs each prompt to `.cursor/prompt-log.jsonl`. |
| `.cursor/prompt-log.jsonl` | Append-only log (one JSON line per prompt). |
| `scripts/analyze-prompts.py` | Reads the log and prints summary + suggested CLAUDE.md sections. |
| `scripts/install.sh` | Installs prompt tracking into another project (hooks + analyzer + .gitignore). |
| `docs/prompt-tracking-for-claude-md.md` | Longer description and log format. |
| `docs/cursor-memory-plugin-design.md` | Design notes and optional memory-store approach. |
