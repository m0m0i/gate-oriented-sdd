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

ROOT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT  # the repo root IS the plugin: see AGENTS.md
errors: list[str] = []


def load(path: pathlib.Path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        errors.append(f"missing: {path.relative_to(ROOT)}")
    except (OSError, UnicodeDecodeError) as e:
        # Present and unreadable, or not decodable. UnicodeDecodeError is a ValueError rather
        # than an OSError, so invalid UTF-8 went on raising through main after this arm was
        # added -- the traceback this arm exists to replace, surviving in the one shape it did
        # not name. This used to leave read_text() to raise through main and
        # exit 1 on a traceback -- fail-closed by accident rather than by decision, and a
        # traceback sends the reader looking for a bug in the guard rather than in the tree.
        errors.append(f"cannot read {path.relative_to(ROOT)}: {e}")
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
# A comparison that could not run is not a comparison that agreed. This was
# `if cc_hooks.is_file() and agy_hooks.is_file():` with no else, so a template renamed, moved
# or unreadable skipped the whole block below and fell through to "both manifests agree" --
# the same sentence, less checking, same exit code. The block is the one thing this guard
# exists for: it pairs Claude Code's SessionStart with Antigravity's PreInvocation, and
# AGENTS.md's parity claim rests on it. load() records absence and unreadability itself, so
# asking it is both the check and the diagnosis. #39.
#
# `is not None` is NOT the test, and that was this fix's own first version: json.loads("null")
# returns None and raises nothing, so a template written as `null` reached the sentinel with
# nothing recorded, skipped the block, and printed the success line -- the defect arriving
# through its own repair. What load() RECORDED is the test, and the shape is checked here
# because the comparison below indexes both documents as objects.
n_before = len(errors)
a = load(cc_hooks)
b = load(agy_hooks)
if len(errors) == n_before:
    for path, doc in ((cc_hooks, a), (agy_hooks, b)):
        if not isinstance(doc, dict):
            # `or {}` used to flatten this into an empty mapping, which produced a named event
            # mismatch. Without it .get() raises, and a traceback is not a diagnosis either.
            errors.append(
                f"{path.relative_to(ROOT)} is valid JSON but not an object "
                f"({type(doc).__name__}), so the two templates cannot be compared"
            )

if isinstance(a, dict) and isinstance(b, dict):
    a_events = set((a.get("hooks") or {}).keys())
    envelope = b.get(cc.get("name") if cc else "", {})
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
    # Claude Code uses SessionStart for steering digest injection; Antigravity uses PreInvocation (turn 1).
    if (a_events - {"SessionStart"}) != (b_events - {"PreInvocation"}):
        errors.append(
            f"hook events differ: Claude Code {sorted(a_events)} vs Antigravity {sorted(b_events)} "
            "(SessionStart on Claude Code pairs with PreInvocation on Antigravity for steering digest)"
        )
    if "SessionStart" not in a_events:
        errors.append("Claude Code hooks template is missing SessionStart for steering digest")
    if "PreInvocation" not in b_events:
        errors.append("Antigravity hooks template is missing PreInvocation for steering digest")


# Antigravity plugin loader discovers rules under rules/ (rules/AGENTS.md).
# AGENTS.md at root is canonical context for Claude Code and this repository;
# rules/AGENTS.md must exist and remain identical to it (typically via symlink).
rules_agents = PLUGIN / "rules" / "AGENTS.md"
root_agents = ROOT / "AGENTS.md"
if not root_agents.is_file():
    errors.append(f"missing: {root_agents.relative_to(ROOT)}")
if not rules_agents.is_file():
    errors.append(f"missing: {rules_agents.relative_to(ROOT)} (required for Antigravity plugin loader rules discovery)")
elif root_agents.is_file():
    try:
        if rules_agents.read_text() != root_agents.read_text():
            errors.append(
                f"{rules_agents.relative_to(ROOT)} has drifted from {root_agents.relative_to(ROOT)}; they must be identical"
            )
    except OSError as e:
        errors.append(f"cannot read {rules_agents.relative_to(ROOT)} or {root_agents.relative_to(ROOT)}: {e}")

if errors:
    print("manifest check FAILED", file=sys.stderr)
    for e in errors:
        print(f"  {e}", file=sys.stderr)
    sys.exit(1)
print("check-manifests: both manifests agree")
