#!/usr/bin/env bash
# Install cursor-postmortem prompt tracking into another project.
# Usage: ./scripts/install.sh /path/to/target/project
#
# Copies the beforeSubmitPrompt hook and merges into the target's .cursor/hooks.json.
# Optionally updates .gitignore and copies the analyzer script so you can run it from the target.

set -e
POSTMORTEM_SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
POSTMORTEM_ROOT="$(cd "$POSTMORTEM_SCRIPT_DIR/.." && pwd)"

usage() {
  echo "Usage: $0 <target-project-dir>"
  echo ""
  echo "  Installs prompt-tracking hook and (optionally) analyzer into the target project."
  echo "  Example: $0 ../my-app"
  exit 1
}

if [ -z "$1" ]; then
  usage
fi
TARGET="$(cd "$1" && pwd)"

if [ ! -d "$TARGET" ]; then
  echo "Error: target is not a directory: $TARGET"
  exit 1
fi

# Copy hook script
mkdir -p "$TARGET/.cursor/hooks"
cp "$POSTMORTEM_ROOT/.cursor/hooks/log-prompt.sh" "$TARGET/.cursor/hooks/log-prompt.sh"
chmod +x "$TARGET/.cursor/hooks/log-prompt.sh"
echo "  Installed .cursor/hooks/log-prompt.sh"

# Merge or create hooks.json
HOOKS_JSON="$TARGET/.cursor/hooks.json"

if [ -f "$HOOKS_JSON" ]; then
  if command -v jq >/dev/null 2>&1; then
    # Set beforeSubmitPrompt to our hook (replacing any existing); preserve other hooks and version
    jq '.hooks.beforeSubmitPrompt = [{"command": ".cursor/hooks/log-prompt.sh"}] | .version = (.version // 1)' \
      "$HOOKS_JSON" > "$HOOKS_JSON.tmp" && mv "$HOOKS_JSON.tmp" "$HOOKS_JSON"
  else
    echo "  Warning: jq not found; could not merge hooks. Add to $HOOKS_JSON manually:"
    echo "    \"beforeSubmitPrompt\": [{\"command\": \".cursor/hooks/log-prompt.sh\"}]"
  fi
  echo "  Updated .cursor/hooks.json"
else
  mkdir -p "$TARGET/.cursor"
  cat > "$HOOKS_JSON" << EOF
{
  "version": 1,
  "hooks": {
    "beforeSubmitPrompt": [
      { "command": ".cursor/hooks/log-prompt.sh" }
    ]
  }
}
EOF
  echo "  Created .cursor/hooks.json"
fi

# Optionally add prompt log to .gitignore
GITIGNORE="$TARGET/.gitignore"
if [ -f "$GITIGNORE" ]; then
  if ! grep -q '\.cursor/prompt-log\.jsonl' "$GITIGNORE" 2>/dev/null; then
    echo "" >> "$GITIGNORE"
    echo "# cursor-postmortem prompt log (local only)" >> "$GITIGNORE"
    echo ".cursor/prompt-log.jsonl" >> "$GITIGNORE"
    echo "  Appended .cursor/prompt-log.jsonl to .gitignore"
  fi
else
  echo "# cursor-postmortem prompt log (local only)" > "$GITIGNORE"
  echo ".cursor/prompt-log.jsonl" >> "$GITIGNORE"
  echo "  Created .gitignore with .cursor/prompt-log.jsonl"
fi

# Copy analyzer so they can run it from the target project
mkdir -p "$TARGET/scripts"
cp "$POSTMORTEM_ROOT/scripts/analyze-prompts.py" "$TARGET/scripts/analyze-prompts.py"
echo "  Installed scripts/analyze-prompts.py"

echo ""
echo "Done. Prompt tracking is installed in: $TARGET"
echo ""
echo "Next steps:"
echo "  1. Open that project in Cursor; prompts will log to .cursor/prompt-log.jsonl"
echo "  2. Run the analyzer from the target project:"
echo "       cd $TARGET"
echo "       python3 scripts/analyze-prompts.py"
echo ""
