#!/usr/bin/env bash
# beforeSubmitPrompt hook: log every user prompt for later analysis.
# Appends to .cursor/prompt-log.jsonl so you can find patterns and decide
# what to add to CLAUDE.md (or .cursor/rules). Does not block submission.
# See https://cursor.com/docs/agent/hooks (beforeSubmitPrompt)

set -e
input=$(cat)
allow() { echo '{"continue": true}'; }

if ! command -v jq >/dev/null 2>&1; then
  allow
  exit 0
fi

# Log path: use first workspace root so global hooks (~/.cursor/) still log per-project
root=$(echo "$input" | jq -r '.workspace_roots[0] // empty')
if [ -n "$root" ]; then
  LOG_FILE="${root}/.cursor/prompt-log.jsonl"
else
  LOG_FILE=".cursor/prompt-log.jsonl"
fi
mkdir -p "$(dirname "$LOG_FILE")"

# Extract fields we care about for pattern analysis
ts=$(date +"%Y-%m-%dT%H:%M:%S%z")
conversation_id=$(echo "$input" | jq -r '.conversation_id // ""')
prompt=$(echo "$input" | jq -r '.prompt // ""')
prompt_len=$(echo "$input" | jq -r '.prompt | length // 0')
# First line of prompt (often the "topic" or intent)
first_line=$(echo "$prompt" | head -n 1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | head -c 200)
attachment_count=$(echo "$input" | jq '.attachments | length // 0')
attachment_types=$(echo "$input" | jq -r '[.attachments[]?.type // empty] | join(",") // ""')

# One JSON object per line (jsonl) for easy append and streaming read
entry=$(jq -n \
  --arg ts "$ts" \
  --arg cid "$conversation_id" \
  --arg prompt "$prompt" \
  --arg first_line "$first_line" \
  --argjson len "$prompt_len" \
  --argjson att "$attachment_count" \
  --arg att_types "$attachment_types" \
  '{ts: $ts, conversation_id: $cid, prompt: $prompt, first_line: $first_line, prompt_length: $len, attachment_count: $att, attachment_types: $att_types}')

echo "$entry" >> "$LOG_FILE"
allow
