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

# Claude Code registers every Markdown file under a plugin's agents/, at any depth, and
# Antigravity's loader processes the directory too. This plugin ships no agents: a reviewer is
# something `init` copies into a project, from reviewers/, and it names a contract and rules
# that exist only there. So the directory existing at all is the defect, empty included, since
# the next file to land in it registers. A CLAUDE.md at the root is the same confusion one
# level up: the validator reads the plugin root as plugin content, and this repository's own
# is .claude/CLAUDE.md. `claude plugin validate --strict` reports both, in CI and too slowly
# for a turn end; this is the copy that runs on one. #235.
for stray, why in (
    ("agents", "both harnesses scan it, and this plugin ships no agents; reviewers live in reviewers/"),
    ("CLAUDE.md", "the validator reads it as plugin content; this repository's own is .claude/CLAUDE.md"),
    # The Claude Code gates ship from .claude-plugin/hooks.json, a path Antigravity's loader
    # does not read (V5, docs/verified.md). Claude Code's default hooks/hooks.json is merged
    # with the declared path and sits inside the directory Antigravity loads; a root hooks.json
    # is Antigravity's own plugin location. Either would carry Claude Code's nested Stop shape
    # into a file Antigravity parses, and one wrong shape invalidates its whole file. #256.
    ("hooks.json", "Antigravity reads a root hooks.json; the Claude Code hooks file is .claude-plugin/hooks.json"),
    ("hooks/hooks.json", "Claude Code merges it with the declared path, and Antigravity loads hooks/; the Claude Code hooks file is .claude-plugin/hooks.json"),
):
    if (PLUGIN / stray).exists() or (PLUGIN / stray).is_symlink():
        shown = stray + "/" if stray == "agents" else stray
        errors.append(f"{shown} exists at the plugin root: {why}")

# While the reviewers were plugin agents, `claude plugin validate` read their frontmatter. They
# are not agents now, so this does: a reviewer `init` copies into a project registers there
# under its `name`, and one without it does not register at all. Everything else under
# reviewers/ is the opposite case. A rulebook, the contract or the starter that gains
# frontmatter registers as an agent in the project's directory, which is what #235 removed
# from the plugin, and until now only a judgment rule (C-7) said so.
#
# Read as lines rather than as YAML: there is no dependency file anywhere in this repository,
# and the two keys asked about are scalars on one line in every reviewer.
def frontmatter(text: str):
    """The frontmatter block's `key: value` lines, or None when the text has no block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    fields = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        if sep and key.strip() and not key[0].isspace():
            fields[key.strip()] = value.strip().strip("\"'")
    return fields


REVIEWERS = PLUGIN / "reviewers"
TEMPLATE = REVIEWERS / "_template" / "reviewer.md"
reviewer_files = sorted(REVIEWERS.glob("*.md"))
if not reviewer_files:
    errors.append("no reviewer found under reviewers/, so no frontmatter was checked")
for path in sorted(REVIEWERS.rglob("*.md")):
    rel = path.relative_to(ROOT)
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError) as e:
        errors.append(f"cannot read {rel}: {e}")
        continue
    fields = frontmatter(text)
    if path not in reviewer_files and path != TEMPLATE:
        if text.lstrip().startswith("---"):
            errors.append(
                f"{rel} carries frontmatter: it is reference material, and with frontmatter it "
                "registers as an agent in the project it is copied into"
            )
        continue
    if fields is None:
        errors.append(f"{rel} has no frontmatter block, so it does not register as a reviewer once installed")
        continue
    # The template's name is `{{REVIEWER_NAME}}` until `init` substitutes it.
    if path != TEMPLATE and fields.get("name") != path.stem:
        errors.append(f"{rel}: frontmatter name {fields.get('name')!r} is not its filename {path.stem!r}")
    for key in ("name", "description"):
        if not fields.get(key):
            errors.append(f"{rel}: frontmatter has no {key}")

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

# The plugin's own Claude Code hooks file (#256). Since 0.23.0 the gates reach a Claude Code
# project from here rather than from a copy `init` made, so this file absent, unregistered or
# naming a script the plugin does not ship is the install-level fail-open: every project on
# the machine runs no gate, and nothing says so. Three things are held: the manifest's "hooks"
# field names it (Claude Code loads a declared path, and hooks/hooks.json is refused above);
# it is a JSON object; and every command in it names a script that exists under hooks/.
# Its events then join the template's below, because the Claude Code side of the parity
# check is now two files: what the plugin runs plus what the project renders.
plugin_hooks = PLUGIN / ".claude-plugin" / "hooks.json"
p_doc = None
if cc:
    declared = cc.get("hooks")
    if not isinstance(declared, str):
        errors.append(
            'Claude Code manifest has no "hooks" field naming .claude-plugin/hooks.json, so the '
            "plugin's gates are not registered on Claude Code"
        )
    elif (PLUGIN / declared).resolve() != plugin_hooks.resolve():
        errors.append(
            f'Claude Code manifest "hooks" names {declared!r}; the plugin\'s hooks file is '
            f"{plugin_hooks.relative_to(ROOT)}"
        )
n_before = len(errors)
p_doc = load(plugin_hooks)
if len(errors) == n_before and not isinstance(p_doc, dict):
    errors.append(
        f"{plugin_hooks.relative_to(ROOT)} is valid JSON but not an object "
        f"({type(p_doc).__name__}), so its hooks cannot be read"
    )
    p_doc = None
def scripts_in(entries) -> set[str]:
    """Every `*.sh` name in a `command` string anywhere under these hook entries. Walks both
    shapes — Claude Code's nested {hooks: [{command}]} and Antigravity's flat {command} — so one
    reader serves the plugin file and the template."""
    found: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            cmd = node.get("command")
            if isinstance(cmd, str):
                found.update(re.findall(r"[A-Za-z0-9_.-]+\.sh", cmd))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(entries)
    return found


p_gates: dict[str, set[str]] = {}
if isinstance(p_doc, dict):
    for event, entries in (p_doc.get("hooks") or {}).items():
        names = scripts_in(entries)
        for name in sorted(names):
            if not (PLUGIN / "hooks" / name).is_file():
                errors.append(
                    f"{plugin_hooks.relative_to(ROOT)} {event}: command names hooks/{name}, "
                    "which the plugin does not ship"
                )
        # Every command goes through the wrapper. A gate run directly from here loses the
        # .steering/ guard and the stand-down, and every project on the machine gets the
        # gate's bootstrap block at Stop. Review round 2.
        for e in entries if isinstance(entries, list) else []:
            if "plugin-gate.sh" not in scripts_in(e):
                errors.append(
                    f"{plugin_hooks.relative_to(ROOT)} {event}: an entry runs "
                    f"{sorted(scripts_in(e) - {'plugin-gate.sh'})} without hooks/plugin-gate.sh"
                )
        # The wrapper is how the gates are run, not a gate; what it is handed is what counts.
        p_gates[event] = names - {"plugin-gate.sh"}

if isinstance(a, dict) and isinstance(b, dict):
    a_events = set((a.get("hooks") or {}).keys())
    if isinstance(p_doc, dict):
        a_events |= set((p_doc.get("hooks") or {}).keys())
    # The template is named groups, each with its own `enabled` (#330): `gate-sdd` holds the digest
    # and both gates, and the fast check has a group of its own so that switching it off leaves
    # the gates on. Events and shapes are read across every group; the gates pair by `gate-sdd`.
    agy_groups = {name: g for name, g in b.items() if isinstance(g, dict)}
    envelope = agy_groups.get(cc.get("name") if cc else "", {})
    b_events = {k for g in agy_groups.values() for k in g if k != "enabled"}

    # Antigravity's schema is mixed: tool events nest under {matcher, hooks:[...]},
    # non-tool events are flat {type, command}. Getting it wrong invalidates the
    # whole file with a misleading error, so check the shapes here rather than
    # discovering it at runtime.
    TOOL_EVENTS = {"PreToolUse", "PostToolUse"}
    for group in agy_groups.values():
        for event, entries in group.items():
            if event == "enabled":
                continue
            for e in entries if isinstance(entries, list) else []:
                nested = isinstance(e, dict) and "hooks" in e
                if event in TOOL_EVENTS and not nested:
                    errors.append(f"antigravity {event}: tool events need the nested {{matcher, hooks:[...]}} form")
                if event not in TOOL_EVENTS and nested:
                    errors.append(f"antigravity {event}: non-tool events need the flat {{type, command}} form")

    # The fast check, held to what #324 measured (docs/verified.md, CLI 1.4.7). Antigravity reads a
    # PostToolUse hook's stdout as its JSON result, so the check runs in a subshell with its output
    # on stderr and the hook prints `{}`; its matcher names the write tools, so it does not run
    # after every read; and it is a group of its own, so `"enabled": false` on it leaves the gates
    # on (#330). Every group ships enabled: a template switched off installs no gate at all.
    gates_group = cc.get("name") if cc else ""
    FAST_GROUP = f"{gates_group}-fast-check"
    FAST_MATCHER = "write_file|edit_file|write_to_file|replace_file_content|multi_replace_file_content"
    FAST_COMMAND = 'cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && ( {{FAST_CHECK}} ) 1>&2; echo \'{}\''
    if set(agy_groups) != {gates_group, FAST_GROUP}:
        errors.append(
            f"antigravity: the template's groups are {sorted(agy_groups)}; they must be exactly "
            f"{gates_group!r}, for the digest and the gates, and {FAST_GROUP!r}, for the fast check"
        )
    for name, group in sorted(agy_groups.items()):
        if group.get("enabled") is not True:
            errors.append(f'antigravity {name}: "enabled" is {group.get("enabled")!r}; every group ships true')
    if "PostToolUse" in envelope:
        errors.append(
            f"antigravity {gates_group}: PostToolUse belongs in {FAST_GROUP}, so that switching the "
            "fast check off does not switch the gates off with it"
        )
    fast = agy_groups.get(FAST_GROUP, {})
    if fast and set(fast) != {"enabled", "PostToolUse"}:
        errors.append(f"antigravity {FAST_GROUP}: holds {sorted(set(fast) - {'enabled'})}; it holds PostToolUse only")
    fast_entries = fast.get("PostToolUse")
    if fast and not (isinstance(fast_entries, list) and len(fast_entries) == 1 and isinstance(fast_entries[0], dict)):
        errors.append(f"antigravity {FAST_GROUP} PostToolUse: one entry, the fast check, is expected")
    elif fast:
        entry = fast_entries[0]
        if entry.get("matcher") != FAST_MATCHER:
            errors.append(
                f"antigravity {FAST_GROUP} PostToolUse: the matcher is {entry.get('matcher')!r}; it must be "
                f"{FAST_MATCHER!r}, the write tools Antigravity CLI 1.4.7 calls and its hooks page names"
            )
        hooks = entry.get("hooks")
        cmd = hooks[0].get("command") if isinstance(hooks, list) and len(hooks) == 1 and isinstance(hooks[0], dict) else None
        if cmd != FAST_COMMAND:
            errors.append(
                f"antigravity {FAST_GROUP} PostToolUse: the command is {cmd!r}; it must be {FAST_COMMAND!r}, "
                "so the check's output goes to stderr and Antigravity's parser reads {}"
            )
    # Claude Code uses SessionStart for steering digest injection; Antigravity uses PreInvocation (turn 0).
    if (a_events - {"SessionStart"}) != (b_events - {"PreInvocation"}):
        errors.append(
            f"hook events differ: Claude Code {sorted(a_events)} (plugin hooks file plus template) "
            f"vs Antigravity {sorted(b_events)} "
            "(SessionStart on Claude Code pairs with PreInvocation on Antigravity for steering digest)"
        )
    if "SessionStart" not in a_events:
        errors.append("Claude Code hooks (plugin file plus template) are missing SessionStart for steering digest")
    # Per gate, for the events both sides declare. The plugin file is now the only place the
    # Claude Code gates are declared, so a Stop that kept one gate and lost the other would
    # ship the lost one to no Claude Code project while the event sets still matched. The
    # digest pairs by event only, because its two scripts have different names by design.
    for event in sorted(set(p_gates) & b_events):
        theirs = scripts_in(envelope.get(event))
        for missing, where in ((theirs - p_gates[event], "Claude Code"), (p_gates[event] - theirs, "Antigravity")):
            if missing:
                errors.append(
                    f"{plugin_hooks.relative_to(ROOT)} {event} runs {sorted(p_gates[event])}, and the "
                    f"Antigravity template runs {sorted(theirs)}: {', '.join(sorted(missing))} missing "
                    f"on {where}"
                )
    if "PreInvocation" not in b_events:
        errors.append("Antigravity hooks template is missing PreInvocation for steering digest")


# Each gate's Stop `timeout` is its ceiling, and the ceiling is written once, in gate-lib.sh (#304,
# AC8). Neither harness turns a timed-out Stop hook into a block, so a gate keeps a deadline of its
# own, and it bounds that deadline by the shortest `timeout` it can see. A file shipped below the
# ceiling therefore lowers every project's budget, and one above it hands the gate a deadline the
# harness kills it before. The three files are the plugin's own (what Claude Code runs), the
# template `init` renders for Antigravity, and this repository's dogfood settings, which run the
# gates from source. The constants are read with anchored patterns and never defaulted: a ceiling
# this cannot find is a comparison that did not run. A release payload ships no .claude/, and,
# as with the directory contracts below, only the sources are required of it.
GATE_LIB = PLUGIN / "hooks" / "gate-lib.sh"
CEILING_OF = {"quality-gate.sh": "_gate_qg_ceiling", "review-gate.sh": "_gate_rg_ceiling"}
ceilings: dict[str, int] = {}
try:
    lib_text = GATE_LIB.read_text()
except (OSError, UnicodeDecodeError) as e:
    errors.append(f"cannot read {GATE_LIB.relative_to(ROOT)}, so the gates' ceilings are unknown: {e}")
    lib_text = None
if lib_text is not None:
    for gate, const in CEILING_OF.items():
        m = re.search(rf"^{const}=([0-9]+)$", lib_text, re.M)
        if m:
            ceilings[gate] = int(m.group(1))
        else:
            errors.append(
                f"{GATE_LIB.relative_to(ROOT)} has no `{const}=<seconds>` line, so the Stop timeout "
                f"{gate} ships with cannot be checked"
            )


def stop_timeouts(stop_entries) -> dict[str, list]:
    """Each gate's `timeout` values under one Stop event, in either shape, keyed by the gate script
    its `command` names. A command that names a gate and carries no `timeout` yields None."""
    found: dict[str, list] = {}

    def walk(node):
        if isinstance(node, dict):
            cmd = node.get("command")
            if isinstance(cmd, str):
                for name in set(re.findall(r"[A-Za-z0-9_.-]+\.sh", cmd)) & set(CEILING_OF):
                    found.setdefault(name, []).append(node.get("timeout"))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(stop_entries)
    return found


dogfood_settings = ROOT / ".claude" / "settings.json"
timeout_files = [(plugin_hooks, p_doc, ("hooks",)), (agy_hooks, b, (cc.get("name") if cc else "",))]
if (ROOT / ".specs").is_dir():
    n_before = len(errors)
    s_doc = load(dogfood_settings)
    if len(errors) == n_before:
        if isinstance(s_doc, dict):
            timeout_files.append((dogfood_settings, s_doc, ("hooks",)))
        else:
            # A comparison that could not run is not one that agreed (#39).
            errors.append(
                f"{dogfood_settings.relative_to(ROOT)} is valid JSON but not an object "
                f"({type(s_doc).__name__}), so the gates' timeouts in it cannot be checked"
            )
if len(ceilings) == len(CEILING_OF):
    for path, doc, envelope_keys in timeout_files:
        rel = path.relative_to(ROOT)
        node = doc
        for k in envelope_keys:
            node = node.get(k) if isinstance(node, dict) else None
        stop = node.get("Stop") if isinstance(node, dict) else None
        if not isinstance(stop, list):
            # The plugin file and the template were loaded above, and their own errors already say
            # why when they are absent; a document that is there and holds no Stop list is new.
            if isinstance(doc, dict):
                errors.append(f"{rel} has no Stop list, so the gates' timeouts in it cannot be checked")
            continue
        found = stop_timeouts(stop)
        for gate, ceiling in sorted(ceilings.items()):
            if gate not in found:
                errors.append(f"{rel} Stop: no entry runs {gate}, so its timeout cannot be held to {ceiling}")
            for t in found.get(gate, []):
                # An integer, exactly: the gates' reader treats 600.0 or "600" as no timeout at all.
                if type(t) is not int or t != ceiling:
                    errors.append(
                        f"{rel} Stop: {gate} has a \"timeout\" of {t!r}, and {GATE_LIB.relative_to(ROOT)}'s "
                        f"{CEILING_OF[gate]} is {ceiling}; the two must agree"
                    )


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

# The three directory contracts init step 3 copies into a project (#83). Each ships under
# assets/directory-contracts/ with its leading dot dropped, and this repository's own copy at
# the dotted path is the one it runs by, so the two must stay identical — otherwise a consumer
# installs a contract this repository no longer holds itself to. The comparison needs the
# dogfood, and a release payload (package-release.py, checked by this script unpacked) ships
# none: a tree without .specs/ is that payload, and only the sources are required of it.
CONTRACTS_SRC = PLUGIN / "assets" / "directory-contracts"
has_dogfood = (ROOT / ".specs").is_dir()
for dogfood in (".specs/README.md", ".specs/_archive/README.md", ".work_logs/README.md"):
    shipped = CONTRACTS_SRC / dogfood.replace(".specs/", "specs/").replace(".work_logs/", "work_logs/")
    local = ROOT / dogfood
    if not shipped.is_file():
        errors.append(f"missing: {shipped.relative_to(ROOT)} (init step 3 copies it to {dogfood})")
    elif not has_dogfood:
        continue
    elif not local.is_file():
        errors.append(f"missing: {dogfood} (this repository's copy of {shipped.relative_to(ROOT)})")
    else:
        try:
            if shipped.read_text() != local.read_text():
                errors.append(f"{shipped.relative_to(ROOT)} has drifted from {dogfood}; they must be identical")
        except OSError as e:
            errors.append(f"cannot read {shipped.relative_to(ROOT)} or {dogfood}: {e}")

if errors:
    print("manifest check FAILED", file=sys.stderr)
    for e in errors:
        print(f"  {e}", file=sys.stderr)
    sys.exit(1)
print("check-manifests: both manifests agree")
