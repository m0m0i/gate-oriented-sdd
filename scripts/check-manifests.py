#!/usr/bin/env python3
"""Verify the dual-manifest plugin is well formed for both harnesses.

One directory is simultaneously a Claude Code plugin and an Antigravity plugin.
Nothing in either toolchain checks that the two halves agree, so this does:
a plugin whose two manifests disagree about its own name installs under two
different identities and its hooks stop matching.

Runs in CI without either CLI installed.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT  # the repo root IS the plugin: see AGENTS.md
errors: list[str] = []


def load(path: pathlib.Path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        errors.append(f"missing: {path.relative_to(ROOT)}")
    except json.JSONDecodeError as e:
        errors.append(f"invalid JSON in {path.relative_to(ROOT)}: {e}")
    return None


cc = load(PLUGIN / ".claude-plugin" / "plugin.json")
agy = load(PLUGIN / "plugin.json")
market = load(ROOT / ".claude-plugin" / "marketplace.json")

if cc and agy:
    if cc.get("name") != agy.get("name"):
        errors.append(f"name mismatch: Claude Code {cc.get('name')!r} vs Antigravity {agy.get('name')!r}")
    # Antigravity restricts the plugin name charset; Claude Code is laxer, so the
    # stricter rule governs the shared name.
    if not re.fullmatch(r"[A-Za-z0-9_-]+", agy.get("name", "")):
        errors.append(f"name {agy.get('name')!r} is not valid for Antigravity (^[a-zA-Z0-9-_]+$)")
    if cc.get("description") != agy.get("description"):
        errors.append("description differs between the two manifests")
    # A version that does not move is a release consumers never receive: the
    # updater reports "already at the latest version" and silently keeps the old
    # content. Both manifests carry it so they cannot drift apart.
    if agy.get("version") and cc.get("version") != agy.get("version"):
        errors.append(f"version mismatch: Claude Code {cc.get('version')!r} vs Antigravity {agy.get('version')!r}")

for field in ("name", "description", "version", "author", "license"):
    if cc and field not in cc:
        errors.append(f"Claude Code manifest is missing {field!r}")

if market and cc:
    entries = [p for p in market.get("plugins", []) if p.get("name") == cc.get("name")]
    if not entries:
        errors.append(f"marketplace.json lists no plugin named {cc.get('name')!r}")
    else:
        src = ROOT / entries[0].get("source", "")
        if not src.is_dir():
            errors.append(f"marketplace source does not exist: {entries[0].get('source')!r}")

# The two hook templates must agree on which lifecycle events they cover, or one
# harness silently enforces less than the other. Their SHAPES differ on purpose —
# see hooks/templates/README.md and docs/verified.md.
cc_hooks = PLUGIN / "hooks" / "templates" / "claude-code.settings.json"
agy_hooks = PLUGIN / "hooks" / "templates" / "antigravity.hooks.json"
if cc_hooks.is_file() and agy_hooks.is_file():
    a = load(cc_hooks) or {}
    b = load(agy_hooks) or {}
    a_events = set((a.get("hooks") or {}).keys())
    envelope = b.get(cc.get("name") if cc else "", {}) if isinstance(b, dict) else {}
    b_events = {k for k in envelope if k != "enabled"}

    # Antigravity's schema is mixed: tool events nest under {matcher, hooks:[...]},
    # non-tool events are flat {type, command}. Getting it wrong invalidates the
    # whole file with a misleading error, so check the shapes here rather than
    # discovering it at runtime.
    TOOL_EVENTS = {"PreToolUse", "PostToolUse"}
    for event, entries in envelope.items():
        if event == "enabled":
            continue
        for e in entries if isinstance(entries, list) else []:
            nested = isinstance(e, dict) and "hooks" in e
            if event in TOOL_EVENTS and not nested:
                errors.append(f"antigravity {event}: tool events need the nested {{matcher, hooks:[...]}} form")
            if event not in TOOL_EVENTS and nested:
                errors.append(f"antigravity {event}: non-tool events need the flat {{type, command}} form")
    # SessionStart has no Antigravity equivalent; it is a documented gap, not drift.
    if (a_events - {"SessionStart"}) != b_events:
        errors.append(
            f"hook events differ: Claude Code {sorted(a_events)} vs Antigravity {sorted(b_events)} "
            "(SessionStart is exempt — Antigravity has no such event)"
        )

if errors:
    print("manifest check FAILED", file=sys.stderr)
    for e in errors:
        print(f"  {e}", file=sys.stderr)
    sys.exit(1)
print("check-manifests: both manifests agree")
