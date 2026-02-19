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


# Common prompt boilerplate to exclude from "recurring topic" suggestions
STOP_PHRASES = frozenset(
    p.strip().lower()
    for p in (
        "how to", "how do i", "can you", "could you", "would you", "please",
        "what is", "what are", "i want", "i need", "i would like", "add a", "add the",
        "fix the", "update the", "change the", "make the", "help me", "show me",
    )
)


def normalize_phrase(s: str) -> str:
    """Lowercase, collapse whitespace, strip."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.strip().lower())


def extract_phrases_from_prompt(prompt: str, min_words: int = 2, max_words: int = 5) -> list[str]:
    """Extract word n-grams from full prompt text; skip leading boilerplate."""
    if not prompt:
        return []
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9]{1,30}\b", prompt.lower())
    seen: set[str] = set()
    out: list[str] = []
    for n in range(max_words, min_words - 1, -1):
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i : i + n])
            if phrase in seen:
                continue
            if len(phrase) < 8:
                continue
            if any(phrase.startswith(prefix) for prefix in STOP_PHRASES):
                continue
            if any(phrase == p or phrase.startswith(p + " ") for p in STOP_PHRASES):
                continue
            seen.add(phrase)
            out.append(phrase)
    return out


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

    # Phrase counts from full prompt text (recurring topics across all prompts)
    phrase_counts: Counter[str] = Counter()
    for e in entries:
        prompt = e.get("prompt") or ""
        for phrase in extract_phrases_from_prompt(prompt):
            phrase_counts[phrase] += 1

    lengths = [e.get("prompt_length", 0) for e in entries]
    with_attachments = sum(1 for e in entries if (e.get("attachment_count") or 0) > 0)

    if not args.suggest_only:
        print("## Prompt log summary")
        print(f"  Total prompts: {len(entries)}")
        print(f"  With attachments: {with_attachments}")
        print(f"  Avg prompt length: {sum(lengths) / len(lengths):.0f} chars")
        print()
        print("## Most frequent phrases (recurring topics across full prompts)")
        for phrase, count in phrase_counts.most_common(20):
            if count < 2:
                break
            print(f"  [{count}x] {phrase[:70]}{'…' if len(phrase) > 70 else ''}")
        print()

    # Suggest CLAUDE.md sections from repeated phrases (from full-prompt analysis)
    repeated = [(phrase, c) for phrase, c in phrase_counts.items() if c >= 2 and len(phrase) >= 8]
    if not repeated:
        if not args.suggest_only:
            print("No repeated phrase patterns yet. Keep using Cursor; re-run after more prompts.")
        return

    print("## Suggested additions for CLAUDE.md (or .cursor/rules)")
    print()
    print("Add context so the AI already knows these; then you can stop re-asking.")
    print()
    for phrase, count in sorted(repeated, key=lambda x: -x[1])[:12]:
        heading = phrase[:60].strip()
        if not heading.endswith("?"):
            heading = heading.rstrip(".")
        print(f"### {heading}")
        print("<!-- Add 1–2 sentences: stack, convention, or decision -->")
        print()
    print("---")
    print("(Generated from full-prompt phrase analysis. Edit CLAUDE.md or .cursor/rules and add the missing context.)")


if __name__ == "__main__":
    main()
