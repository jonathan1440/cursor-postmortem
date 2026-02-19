# How to Build a Cursor “Memory” Plugin (Article-Style)

This doc describes how to build something like the system in [“I Gave Claude Code a Memory and Now It Judges My Coding Habits”](https://medium.com/@rentierdigital/i-gave-claude-code-a-memory-and-now-it-judges-my-coding-habits-heres-how-9eae1e1b4a4f): persistent context so the AI doesn’t start each session from zero, and so it can *tell you* what it needed to know (instead of you guessing what to put in CLAUDE.md).

## What the Article Is Solving

- **Problem**: Every new session, the AI has no memory of the project, past decisions, or your habits. You re-explain and re-teach.
- **CLAUDE.md**: Helps, but you don’t know what to put in it (“documentation based on vibes and trauma”).
- **Idea**: The AI observes work and *tells you what it needed to know*; you automate capture so that becomes the memory.

The author’s “47 lines of bash” is about automating that loop (likely: capture events → feed or summarize → update a context file). **Cursor has a full hook system** ([Cursor Hooks](https://cursor.com/docs/agent/hooks)): scripts run before/after tool use, at session start/end, and more. That changes how we implement “memory”: we can **inject context at session start** and optionally **log tool use** for session continuity, in addition to (or instead of) relying on the AI to call MCP first.

## Cursor vs Claude Code

| Aspect | Claude Code | Cursor |
|--------|-------------|--------|
| Project context | `CLAUDE.md`, `.claude/` | `.cursor/rules/`, optional `AGENTS.md`, project files |
| Hooks | Yes (e.g. PostToolUse in settings) | **Yes** – [sessionStart, sessionEnd, preToolUse, postToolUse, afterFileEdit, beforeShellExecution, afterMCPExecution](https://cursor.com/docs/agent/hooks), etc. |
| Extensibility | Claude Code plugins | VS Code extensions + **MCP** + **hooks** |
| “Memory” injection | Auto from files + hooks | **sessionStart** can return `additional_context`; rules; MCP tools |

So a “plugin” for Cursor that gives the AI a memory can be:

1. **Hooks + MCP** – **sessionStart** hook reads the memory store and returns it as `additional_context`, so every new session gets memory without the AI calling a tool. MCP still gives the AI `memory_store` / `memory_search` / `memory_list` to *write* and query memory during the session. Optional **postToolUse** (e.g. matcher for MCP or file edits) to log activity; **sessionEnd** to archive or summarize.
2. **MCP only** – AI calls `memory_list` or `memory_search` at start (via a rule). Simpler, but memory loads only after the first turn.
3. **File-based + rule** – Session file (e.g. `.cursor/NOW.md`) updated by scripts or a **postToolUse** / **afterFileEdit** hook; rule says “read this file first.” Optional **sessionStart** hook injects that file as `additional_context`.

Below we focus on (1) as the strongest option now that Cursor hooks exist, then (2) and (3).

---

## Approach A: MCP Memory Server (AI-Controlled Memory)

The AI literally has a memory: it can **store** and **recall** facts. “What it needed to know” becomes: at the end of a session (or when something important happens), the agent calls a tool to save it; at the start of the next session, a rule tells the agent to call a tool to load recent memory.

### Why this fits the article

- The AI “tells you what it needed to know” by **calling a store tool** (e.g. “remember: auth is Supabase + RLS; do not use Firebase”).
- No guessing what to put in CLAUDE.md; the AI records what was missing or what it learned.
- You can later promote important items from “memory” into `.cursor/rules` or a project doc.

### High-level design

- **MCP server** (e.g. Node/Bun/Python) that:
  - Exposes tools: e.g. `memory_store({ key, value, tags })`, `memory_search(query)`, `memory_list()`, maybe `memory_delete(id)`.
  - Persists to disk (SQLite or JSON in `.cursor/memory/` or a user dir) so it survives restarts.
- **Cursor**: Add this server in Cursor Settings → MCP.
- **sessionStart hook** (recommended): A script that reads `.cursor/memory/store.json`, formats the last N entries as text, and returns `{ "additional_context": "## Project memory\n\n..." }`. Then every new session gets memory in the initial system context without the AI having to call a tool first. See [Cursor Hooks – sessionStart](https://cursor.com/docs/agent/hooks).
- **Rule** (e.g. `.cursor/rules/memory.mdc` with `alwaysApply: true`):
  - “When you learn something important (stack, conventions, decisions, user preferences), call `memory_store` so future sessions have context.”

### Minimal implementation sketch (Node MCP server)

- One process that:
  - Listens on stdio (or SSE) for MCP requests.
  - Implements `memory_store` (append to a JSON array or SQLite table with `key`, `value`, `tags`, `timestamp`), `memory_search` (simple substring or tag match, or embed and use a vector search if you want), `memory_list` (last N entries).
  - Reads/writes a file under the project or `~/.cursor-memory/<project-id>.json`.
- Publish the server so Cursor can run it (e.g. `npx` or a local path in MCP config).

### Cursor rule example

```markdown
---
description: Load and update project memory across sessions
alwaysApply: true
---

# Project memory

- At session start: call MCP tool `memory_search` with query "recent context" or "project decisions" (or `memory_list`) and use the result to restore context.
- When you learn something that should persist (tech choices, file layout, conventions, user corrections): call `memory_store` with a short key and clear value so future sessions see it.
- Prefer storing concise facts, not long paragraphs.
```

Result: the AI “judges” your habits only in the sense that it records what it needed (e.g. “use Supabase, not Firebase”) and reapplies it next time. You’re not writing that by hand; the AI does it via the tool.

---

## Approach B: File-Based Session Memory (No MCP)

Closer to the “47 lines of bash” idea: a **session log** file that gets updated automatically; the AI is told to read it every session. The “AI tells you what it needed to know” part can be a separate step (e.g. end-of-session prompt that appends to the file, or a script that calls an API to summarize and append).

### High-level design

- **Session file**: e.g. `.cursor/NOW.md` or `.cursor/session-memory.md` (or under `.claude/` if you want to mirror Claude Code layout).
- **Who writes to it**:
  - **Option B1 – Manual / AI-assisted**: You (or the AI when you ask) append bullets: “We use Supabase for auth. Don’t add Firebase.” A rule says: “Read `.cursor/NOW.md` at session start.”
  - **Option B2 – Scripts**: A small script (bash or Node) that runs on a timer or via a VS Code extension on save: e.g. append “Edited: file path, time” to a log. So the file has a “what changed recently” section. The AI is told to read it for continuity.
  - **Option B3 – Extension**: A VS Code extension that subscribes to `onDidChangeTextDocument` (and optionally `onDidRunTerminalCommand`), and appends to `.cursor/session-memory.md` with timestamps and file names (and optionally a short diff or “summary” line). Again, a rule tells the AI to read this file first.
- **“AI tells you what it needed to know”**: At end of session you ask: “What should we add to project memory?” and paste the AI’s answer into the file, or run a script that calls an API to get a short summary and appends it.

### Minimal “47 lines” style (bash + rule)

- **Rule**: “Read `.cursor/NOW.md` at the start of each session. It contains current focus and recent decisions.”
- **Script** (e.g. `~/.cursor/scripts/append-now.sh`): Appends a line to `.cursor/NOW.md` with timestamp and first argument (e.g. “$ date; echo $1”). You run it manually or from a tiny VS Code task when you switch context.
- **Optional**: A second script that runs `git diff --name-only` and appends “Files changed: …” so the AI sees what was touched.

No plugin binary: just a rule + a file + optional scripts. The “plugin” is the convention plus the rule.

---

## Approach C: Hybrid (MCP + File Log)

- **MCP server**: For semantic, long-lived memory (decisions, stack, preferences). AI uses `memory_store` / `memory_search`.
- **File**: `.cursor/NOW.md` or similar for “this session we’re doing X” and “last session we did Y,” updated by you or by an extension that logs recent edits. Rule: “Read NOW.md then call memory_search for project context.”

Gives you both “what we’re doing right now” and “what we decided before.”

---

## Recommendation (with Cursor hooks)

- **Best**: **Approach A + sessionStart hook** – MCP server for store/search/list; a **sessionStart** hook that reads `.cursor/memory/store.json` and returns `additional_context`. Memory is in the first message every time; the AI still uses MCP to *write* memory during the session. One rule: “When you learn something important, call `memory_store`.”
- **Optional**: **postToolUse** hook with matcher for `MCP` or for your memory tool names, to append “Tool X used at …” to a session log (e.g. `.cursor/NOW.md`) for continuity. **sessionEnd** can append a one-line summary or archive the session.
- **Closest to the article’s “bash + file”**: **Approach B** with a **sessionStart** hook that injects `.cursor/NOW.md` as `additional_context`, plus a **postToolUse** or **afterFileEdit** hook that appends to that file.
- **Most complete**: **Approach C** – MCP + sessionStart injection + optional file log and sessionEnd archive.

---

## References

- [Cursor Hooks](https://cursor.com/docs/agent/hooks) – sessionStart, sessionEnd, preToolUse, postToolUse, afterFileEdit, afterMCPExecution, etc. Hooks receive JSON on stdin and return JSON on stdout; **sessionStart** can return `additional_context` to inject memory into every new session.
- [Cursor Rules](https://cursor.com/docs/context/rules) – project rules and when they’re included.
- [Cursor MCP](https://cursor.directory/) – adding MCP servers so the agent can call tools.
- [claude-memory-template](https://github.com/bit2space/claude-memory-template) – Claude Code hook-based memory (NOW.md, PROGRESS.md, DECISIONS.md).
- [claude-mem Cursor integration](https://docs.claude-mem.ai/cursor) – Cursor memory via worker + hooks.

**Implementation in this repo:**
- **Prompt tracking (no memory store):** Log every prompt and analyze patterns to decide what to add to CLAUDE.md. See [Prompt tracking for CLAUDE.md](prompt-tracking-for-claude-md.md): **beforeSubmitPrompt** → `.cursor/hooks/log-prompt.sh` writes to `.cursor/prompt-log.jsonl`; `scripts/analyze-prompts.py` suggests doc sections from repeated intents.
- **Optional memory store:** `memory-server/` (MCP), `.cursor/rules/memory.mdc`, and `.cursor/hooks/session-start-memory.sh` (sessionStart). Add the MCP server in Cursor Settings → MCP; hooks load automatically. The sessionStart hook requires `jq`.
