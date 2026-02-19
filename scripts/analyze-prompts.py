#!/usr/bin/env python3
"""
Read .cursor/prompt-log.jsonl (written by the beforeSubmitPrompt hook),
find patterns, and suggest sections to add to CLAUDE.md or .cursor/rules.

Usage:
  python3 scripts/analyze-prompts.py                    # print summary + suggestions
  python3 scripts/analyze-prompts.py --suggest-only     # only suggested doc sections
  python3 scripts/analyze-prompts.py --log path         # use custom log file
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

# Default log location (project root relative to script or cwd)
DEFAULT_LOG = Path(".cursor/prompt-log.jsonl")


def load_log(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    out = []
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def normalize_first_line(s: str) -> str:
    """Normalize for grouping: lowercase, collapse spaces, take first 80 chars."""
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s.strip().lower())
    return s[:80]


def extract_key_phrases(prompt: str, max_words: int = 4) -> list[str]:
    """Very simple phrase extraction: consecutive word runs that look like topics."""
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9]{1,24}\b", prompt.lower())
    phrases = []
    for i in range(len(words) - max_words + 1):
        phrase = " ".join(words[i : i + max_words])
        if len(phrase) > 10 and not phrase.startswith(("how to", "what is", "can you")):
            phrases.append(phrase)
    return phrases


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze logged prompts and suggest CLAUDE.md content")
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG, help="Path to prompt log (jsonl)")
    ap.add_argument("--suggest-only", action="store_true", help="Only print suggested doc sections")
    args = ap.parse_args()

    entries = load_log(args.log)
    if not entries:
        if not args.suggest_only:
            print("No prompts logged yet. Send some messages in Cursor (with beforeSubmitPrompt hook enabled).", file=sys.stderr)
        return

    # Patterns: first-line frequency (what you keep asking)
    first_lines = [normalize_first_line(e.get("first_line", "")) for e in entries if e.get("first_line")]
    first_line_counts = Counter(first_lines)

    # Full prompt length and attachment stats
    lengths = [e.get("prompt_length", 0) for e in entries]
    with_attachments = sum(1 for e in entries if (e.get("attachment_count") or 0) > 0)

    if not args.suggest_only:
        print("## Prompt log summary")
        print(f"  Total prompts: {len(entries)}")
        print(f"  With attachments: {with_attachments}")
        print(f"  Avg prompt length: {sum(lengths) / len(lengths):.0f} chars")
        print()
        print("## Most frequent first lines (recurring intents)")
        for line, count in first_line_counts.most_common(15):
            if not line or count < 2:
                continue
            print(f"  [{count}x] {line[:70]}{'…' if len(line) > 70 else ''}")
        print()

    # Suggest CLAUDE.md sections from repeated first lines
    repeated = [(line, c) for line, c in first_line_counts.items() if c >= 2 and line]
    if not repeated:
        if not args.suggest_only:
            print("No repeated first-line patterns yet. Keep using Cursor; re-run after more prompts.")
        return

    print("## Suggested additions for CLAUDE.md (or .cursor/rules)")
    print()
    print("Add context so the AI already knows these; then you can stop re-asking.")
    print()
    for line, count in sorted(repeated, key=lambda x: -x[1])[:12]:
        # Turn a repeated prompt start into a doc heading + placeholder
        heading = line[:50].strip()
        if not heading.endswith("?"):
            heading = heading.rstrip(".")
        print(f"### {heading}")
        print("<!-- Add 1–2 sentences: stack, convention, or decision -->")
        print()
    print("---")
    print("(Generated from prompt log. Edit CLAUDE.md or .cursor/rules and add the missing context.)")


if __name__ == "__main__":
    main()
