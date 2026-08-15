#!/usr/bin/env python3
"""Render a Claude Code session .jsonl transcript into readable Markdown.

Keeps the conversation narrative (user prompts, assistant replies), shows each
tool call as a one-line bullet, and tucks truncated tool output into collapsed
<details> blocks so GitHub renders a skimmable page. The .jsonl files remain the
complete record; this is the reading view.

Usage: python3 render.py <session.jsonl> [more.jsonl ...]
Writes <session>.md next to each input.
"""

import json
import re
import sys
from pathlib import Path

TOOL_INPUT_LIMIT = 220      # chars of tool input shown on the bullet line
TOOL_RESULT_LIMIT = 500     # chars of tool output kept inside <details>
SKILL_BODY_LIMIT = 250      # chars kept of harness-injected skill instructions
SPLIT_KB = 460              # split output files bigger than this (GitHub stops rendering ~512 KB)
SYSTEM_TAG_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)


def is_skill_payload(text: str) -> bool:
    """Harness-injected skill instructions arrive as a 'user' turn; they aren't the human."""
    t = text.lstrip()
    return t.startswith("Base directory for this skill:") or t.startswith("(Re-invocation of")


def clean_user_text(text: str) -> str:
    """Drop harness-injected wrappers, keep what the human actually typed."""
    text = SYSTEM_TAG_RE.sub("", text)
    for tag in ("local-command-caveat", "command-message", "local-command-stdout"):
        text = re.sub(rf"<{tag}>.*?</{tag}>", "", text, flags=re.DOTALL)
    # A /command invocation: the visible prompt is the command name plus whatever the
    # user typed after it — the args ARE the user's message (e.g. the whole
    # brainstorming prompt arrives as /superpowers:brainstorming <prompt>), so they
    # must be kept, not stripped as harness noise.
    name = re.search(r"<command-name>(.*?)</command-name>", text, re.DOTALL)
    args = re.search(r"<command-args>(.*?)</command-args>", text, re.DOTALL)
    if name:
        text = re.sub(r"<command-name>.*?</command-name>", "", text, flags=re.DOTALL)
        text = re.sub(r"<command-args>.*?</command-args>", "", text, flags=re.DOTALL)
        arg_text = args.group(1).strip() if args else ""
        text = f"`{name.group(1).strip()}` {arg_text}\n\n{text}"
    return text.strip()


def truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + f"\n… [{len(text) - limit:,} more chars — see the .jsonl]"


def fence(text: str) -> str:
    ticks = "```"
    while ticks in text:
        ticks += "`"
    return f"{ticks}\n{text}\n{ticks}"


def compact_input(tool_input: dict) -> str:
    """One-line summary of a tool call's input."""
    if not isinstance(tool_input, dict):
        return truncate(str(tool_input), TOOL_INPUT_LIMIT)
    for key in ("command", "file_path", "prompt", "pattern", "query", "skill", "url"):
        if key in tool_input:
            val = str(tool_input[key]).replace("\n", " ⏎ ")
            extra = ""
            if key == "file_path" and len(tool_input) > 1:
                extra = " (+edit)" if "old_string" in tool_input or "content" in tool_input else ""
            return truncate(f"{key}={val}{extra}", TOOL_INPUT_LIMIT)
    return truncate(json.dumps(tool_input, ensure_ascii=False), TOOL_INPUT_LIMIT)


def result_text(content) -> str:
    """Flatten a tool_result's content to text; images become a placeholder."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if isinstance(block, dict):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "image":
                parts.append("[image/screenshot omitted]")
    return "\n".join(parts)


def render(path: Path) -> Path:
    out_lines = [f"# Transcript: {path.stem}", ""]
    tool_names = {}  # tool_use id -> name, so results can be labelled

    with path.open() as fh:
        for line in fh:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            etype = entry.get("type")
            ts = (entry.get("timestamp") or "")[:16].replace("T", " ")

            if etype == "user":
                content = entry.get("message", {}).get("content")
                if isinstance(content, str):
                    if is_skill_payload(content):
                        out_lines += [
                            "<details><summary>📚 skill instructions loaded (collapsed)</summary>\n\n"
                            f"{fence(truncate(content, SKILL_BODY_LIMIT))}\n\n</details>", ""]
                        continue
                    text = clean_user_text(content)
                    if text:
                        out_lines += [f"## 🧑 User — {ts}", "", text, ""]
                elif isinstance(content, list):
                    texts, results = [], []
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") == "text":
                            raw = block.get("text", "")
                            if is_skill_payload(raw):
                                results.append(
                                    "<details><summary>📚 skill instructions loaded (collapsed)</summary>\n\n"
                                    f"{fence(truncate(raw, SKILL_BODY_LIMIT))}\n\n</details>")
                                continue
                            cleaned = clean_user_text(raw)
                            if cleaned:
                                texts.append(cleaned)
                        elif block.get("type") == "tool_result":
                            name = tool_names.get(block.get("tool_use_id"), "tool")
                            body = truncate(result_text(block.get("content")), TOOL_RESULT_LIMIT)
                            if body:
                                flag = " ⚠️ error" if block.get("is_error") else ""
                                results.append(
                                    f"<details><summary>⤷ {name} result{flag}</summary>\n\n"
                                    f"{fence(body)}\n\n</details>"
                                )
                    if texts:
                        out_lines += [f"## 🧑 User — {ts}", ""] + texts + [""]
                    out_lines += results
                    if results:
                        out_lines.append("")

            elif etype == "assistant":
                blocks = entry.get("message", {}).get("content", [])
                texts, calls = [], []
                for block in blocks:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text" and block.get("text", "").strip():
                        texts.append(block["text"].strip())
                    elif block.get("type") == "tool_use":
                        tool_names[block.get("id")] = block.get("name", "tool")
                        calls.append(f"- 🔧 **{block.get('name')}** · `{compact_input(block.get('input', {}))}`")
                    # thinking blocks intentionally skipped
                if texts:
                    out_lines += [f"### 🤖 Assistant — {ts}", ""] + texts + [""]
                if calls:
                    out_lines += calls + [""]

    text = "\n".join(out_lines)
    out_path = path.with_suffix(".md")
    if len(text.encode()) <= SPLIT_KB * 1024:
        out_path.write_text(text)
        return [out_path]

    # Too big for GitHub to render: split into parts at user-turn boundaries.
    chunks, current, size = [], [], 0
    for block in text.split("\n## 🧑 User")[0:]:
        piece = ("\n## 🧑 User" + block) if chunks or current else block
        if size + len(piece) > SPLIT_KB * 1024 and current:
            chunks.append("".join(current))
            current, size = [], 0
        current.append(piece)
        size += len(piece)
    if current:
        chunks.append("".join(current))
    paths = []
    for i, chunk in enumerate(chunks, 1):
        part = path.with_name(f"{path.stem}-part{i}.md")
        header = "" if i == 1 else f"# Transcript: {path.stem} (part {i}/{len(chunks)})\n"
        part.write_text(header + chunk)
        paths.append(part)
    return paths


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        for p in render(Path(arg)):
            print(f"{p}  ({p.stat().st_size / 1024:.0f} KB)")
