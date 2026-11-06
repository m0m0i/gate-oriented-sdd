#!/usr/bin/env python3
"""Report, and on request write, what a re-run of `init` changes in an Antigravity install (#343).

On Antigravity `init` copies the gates and the harness checks into `.agents/hooks/` and renders
`.agents/hooks.json` from the plugin's template, so a fix the plugin ships reaches an existing
install only when `init` runs again. This script is that re-run's deterministic half. It reads
`assets/shipped-texts.json`, the plugin's table of every text each copied file has had on the
default branch, and sorts each copy into one of four classes:

  current   its text is the plugin's current text
  shipped   its text is an earlier text of this plugin, so it is replaced
  missing   it is absent, so it is added
  edited    its text is one this plugin never shipped: the project's edit, replaced only when named

It reports and writes nothing unless `--write` is given, and it writes only what the report
proposes and the answers allow: an `edited` copy only with `--replace <path>`, the hooks file
only with `--hooks-json`. The copies and the hooks file are one unit: the copies are written
only when the hooks file will be current after the run, because a refreshed gate under an older
hooks file runs with that file's `timeout`s (`skills/init/SKILL.md:77`).

Targets are read from the disk, never assumed. Antigravity is a target when `.agents/hooks.json`
or `.agents/hooks/` exists. A reviewer contract copy is classified wherever `init` put one. A
pre-0.41.0 install's `scripts/` guards are classified and reported, and never written: #340's
migration removes them. With no target the script says `no install` (exit 4), unless `--install`
asks it to make an Antigravity install.

Exit codes: 0 nothing to upgrade or all applied; 3 changes or questions pending; 4 no install;
1 a refusal (not a repository, the plugin's own tree, an unreadable file, a stale table, a write
that failed part-way). A refusal is never 0. With more than one `--project` it reports on each,
writes nothing, and exits with the worst code: 1 over 3 over 4 over 0.

Python 3 stdlib only. It runs from the plugin directory `init` installs from.
"""

import argparse
import difflib
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

PLUGIN = pathlib.Path(__file__).resolve().parent.parent
TABLE = PLUGIN / "assets" / "shipped-texts.json"
TEMPLATE = PLUGIN / "hooks" / "templates" / "antigravity.hooks.json"
HOOKS_JSON = ".agents/hooks.json"
HOOKS_DIR = ".agents/hooks"
QUALITY_GATE = ".agents/hooks/quality-gate.sh"
HARNESS_CHECKS = (
    "check-steering-anchors.sh",
    "check-locks.py",
    "check-document-set.py",
    "check-document-cascade.py",
)
EXIT_OK, EXIT_REFUSED, EXIT_PENDING, EXIT_NO_INSTALL = 0, 1, 3, 4
WORST = (EXIT_REFUSED, EXIT_PENDING, EXIT_NO_INSTALL, EXIT_OK)


class Refusal(Exception):
    """A state the script will not judge: it names the path and why, and exits 1."""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_table():
    try:
        table = json.loads(TABLE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Refusal(f"the plugin's table {TABLE} cannot be read: {e}") from e
    current = {}
    sources = (
        set(table["copy_set"].values())
        | {table["contract"]["source"]}
        | set(table["legacy_guards"].values())
    )
    for src in sorted(sources):
        try:
            h = sha((PLUGIN / src).read_bytes())
        except OSError as e:
            raise Refusal(f"the plugin's {src} cannot be read: {e}") from e
        if h not in table["texts"].get(src, []):
            raise Refusal(
                f"the plugin's table is stale: {src}'s text is not in {TABLE.name}, "
                "so it cannot tell a text this plugin shipped from an edit. "
                "Reinstall the plugin from a release or a clean clone."
            )
        current[src] = h
    try:
        tpl = sha(TEMPLATE.read_bytes())
    except OSError as e:
        raise Refusal(f"the plugin's template {TEMPLATE} cannot be read: {e}") from e
    if tpl not in table["templates"]:
        raise Refusal(
            "the plugin's table is stale: hooks/templates/antigravity.hooks.json's text is not in "
            f"{TABLE.name}. Reinstall the plugin from a release or a clean clone."
        )
    return table, current


def project_root(arg):
    path = pathlib.Path(arg)
    if not path.is_dir():
        raise Refusal(f"{arg} is not a directory")
    r = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if r.returncode != 0:
        raise Refusal(f"{arg} is not inside a git repository, so there is no project to upgrade")
    root = pathlib.Path(r.stdout.strip()).resolve()
    if root == PLUGIN or PLUGIN in root.parents:
        raise Refusal(f"{root} is the plugin's own tree, not a project it installed into")
    return root


def classify(root, rel, src, table, current):
    """One copy's class: (class, detail). Raises Refusal for a state it will not judge."""
    path = root / rel
    if path.is_symlink():
        return "symlink", os.readlink(path)
    if not os.path.lexists(path):
        return "missing", None
    if not path.is_file():
        raise Refusal(f"{rel} is not a regular file, so its text cannot be read")
    try:
        data = path.read_bytes()
    except OSError as e:
        raise Refusal(f"{rel} cannot be read: {e}") from e
    h = sha(data)
    if h == current[src]:
        return "current", None
    if h in table["texts"].get(src, []):
        return "shipped", None
    return "edited", data


def render(template_text, fast_check):
    """The template with its two placeholders substituted in the parsed structure, never in text."""

    def walk(v):
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, str):
            return v.replace("{{HOOKS_DIR}}", HOOKS_DIR).replace("{{FAST_CHECK}}", fast_check)
        return v

    return walk(json.loads(template_text))


def dump(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


GATES = {
    "quality-gate.sh": "quality",
    "review-gate.sh": "review",
    "steering-digest-antigravity.sh": "digest",
}
FAST_GROUP = "gate-sdd-fast-check"


def hooks_of(entry):
    """An entry's hook dicts: a tool event nests them under `hooks`, the others are flat."""
    if not isinstance(entry, dict):
        return []
    inner = entry.get("hooks")
    return [h for h in inner if isinstance(h, dict)] if isinstance(inner, list) else [entry]


def entry_key(event, entry):
    """What an entry runs: a gate or the digest by the script its command names, else the fast
    check by being a PostToolUse entry. Entries are aligned by this, never by position."""
    for h in hooks_of(entry):
        cmd = h.get("command", "")
        for script, key in GATES.items():
            if isinstance(cmd, str) and script in cmd:
                return key
    return "fast" if event == "PostToolUse" else None


def slots(obj):
    """(group, event, key) to (index, entry), for the first entry of each key in each list."""
    out = {}
    for g, group in obj.items():
        if not isinstance(group, dict):
            continue
        for ev, entries in group.items():
            if not isinstance(entries, list):
                continue
            for i, e in enumerate(entries):
                k = entry_key(ev, e)
                if k and (g, ev, k) not in out:
                    out[(g, ev, k)] = (i, e)
    return out


def capture(pattern, cmd):
    """The fast check inside `cmd`, read through the template's envelope `pattern`, or None."""
    if not isinstance(cmd, str):
        return None
    head, _, tail = pattern.replace("{{HOOKS_DIR}}", HOOKS_DIR).partition("{{FAST_CHECK}}")
    m = re.fullmatch(re.escape(head) + "(.*)" + re.escape(tail), cmd, re.S)
    return m.group(1) if m else None


def fit(template, project):
    """How `template` explains `project`: a dict, or None when a gate's entry has no place in it.

    Every value the template owns is compared: equal, captured by `{{FAST_CHECK}}`, or recorded
    as a difference. A template-owned entry the project lacks is recorded as deleted. The score
    is what the fit leaves unexplained, so the template that wrote a file scores lowest."""
    tslots, pslots = slots(template), slots(project)
    deleted = [s for s in tslots if s not in pslots]
    if any(s[2] in ("quality", "review") for s in deleted):
        return None
    diffs, fast, fast_cmd, edited_gates = [], None, None, []
    for s, (_ti, te) in tslots.items():
        if s not in pslots:
            continue
        _pi, pe = pslots[s]
        if "matcher" in te and pe.get("matcher") != te["matcher"]:
            diffs.append((s, "matcher"))
        th, ph = hooks_of(te), hooks_of(pe)
        if not ph:
            diffs.append((s, "shape"))
            continue
        for key, tval in th[0].items():
            pval = ph[0].get(key)
            if key == "command" and s[2] == "fast":
                fast_cmd = pval
                fast = capture(tval.replace("{{HOOKS_DIR}}", HOOKS_DIR), pval)
                if fast is None:
                    diffs.append((s, "command"))
            elif key == "command":
                if pval != tval.replace("{{HOOKS_DIR}}", HOOKS_DIR):
                    diffs.append((s, "command"))
                    edited_gates.append(s[2])
            elif pval != tval:
                diffs.append((s, key))
    for g, group in template.items():
        pg = project.get(g)
        if isinstance(pg, dict) and pg.get("enabled") is not group.get("enabled"):
            diffs.append(((g, None, None), "enabled"))
    # An entry the project runs under a key the template owns, in a place the template does not
    # carry, is unexplained by it: the untagged cd-only template has no PreInvocation, so without
    # this a v0.21.0 render's digest entry would read as the project's and the two would tie.
    unexplained = [s for s in pslots if s not in tslots and s[0] in template]
    return {
        "score": len(diffs) + len(unexplained) + 100 * len(deleted),
        "diffs": diffs,
        "deleted": deleted,
        "fast": fast,
        "fast_cmd": fast_cmd,
        "edited_gates": edited_gates,
        "tslots": tslots,
        "pslots": pslots,
    }


def identify(project, templates):
    """The (sha, template, fit) that wrote `project`, or None when no single template fits best."""
    fits = []
    for k, text in templates.items():
        tpl = json.loads(text)
        f = fit(tpl, project)
        if f is not None:
            fits.append((f["score"], k, tpl, f))
    if not fits:
        return None, "fits no template this plugin shipped since v0.2.3"
    fits.sort(key=lambda x: x[0])
    if len(fits) > 1 and fits[0][0] == fits[1][0]:
        return None, f"fits two templates equally ({fits[0][1][:12]} and {fits[1][1][:12]})"
    _score, k, tpl, f = fits[0]
    return (k, tpl, f), None


def merge_project_values(cur, project, tpl, f, args, out):
    """Carry what the project chose onto the current template's rendering `cur`."""
    cslots = slots(cur)
    # The fast check's matcher, where it differs from the identifying template's own.
    tfast = [s for s in f["tslots"] if s[2] == "fast"]
    cfast = [s for s in cslots if s[2] == "fast"]
    if tfast and cfast and tfast[0] in f["pslots"]:
        pm = f["pslots"][tfast[0]][1].get("matcher")
        tm = f["tslots"][tfast[0]][1].get("matcher")
        if pm is not None and pm != tm:
            cslots[cfast[0]][1]["matcher"] = pm
    # Keys the project added to a template-owned hook are kept.
    for s, (_ti, te) in f["tslots"].items():
        if s not in f["pslots"]:
            continue
        cs = [c for c in cslots if c[2] == s[2] and (c[1] == s[1])]
        if not cs:
            continue
        th, ph, ch = hooks_of(te), hooks_of(f["pslots"][s][1]), hooks_of(cslots[cs[0]][1])
        if th and ph and ch:
            for key, val in ph[0].items():
                if key not in th[0]:
                    ch[0][key] = val
    # Every entry the template does not own is the project's, kept where it stood.
    owned = {(s[0], s[1], f["pslots"][s][0]) for s in f["tslots"] if s in f["pslots"]}
    for g, group in project.items():
        if not isinstance(group, dict):
            continue
        if g not in tpl:
            cur.setdefault(g, group)
            continue
        for ev, entries in group.items():
            if not isinstance(entries, list):
                if ev != "enabled" and ev not in tpl[g]:
                    cur.setdefault(g, {})[ev] = entries
                continue
            first_owned = min([i for (og, oe, i) in owned if og == g and oe == ev], default=None)
            for i, e in enumerate(entries):
                if (g, ev, i) in owned:
                    continue
                target = cur.setdefault(g, {"enabled": True}).setdefault(ev, [])
                if first_owned is not None and i < first_owned:
                    target.insert(i, e)
                else:
                    target.append(e)
    # The fast-check group's `enabled`, where the identifying template had that group.
    pfast = project.get(FAST_GROUP)
    if FAST_GROUP in tpl and isinstance(pfast, dict) and FAST_GROUP in cur:
        cur[FAST_GROUP]["enabled"] = pfast.get("enabled")
    gate_group = "gate-sdd"
    off = gate_group in project and project[gate_group].get("enabled") is not True
    if off and FAST_GROUP not in tpl:
        if args.fast_check_enabled is None:
            out["blocking"].append(
                f"{HOOKS_JSON}: its one `gate-sdd` group has `enabled` false, which switched the "
                "gates and the fast check off together. The proposal turns the gates on and the "
                "fast check off; answer with --fast-check-enabled true|false"
            )
        if FAST_GROUP in cur:
            cur[FAST_GROUP]["enabled"] = args.fast_check_enabled == "true"
    elif off:
        out["asks"].append(
            f"{HOOKS_JSON}: the gate-sdd group is switched off, so neither gate runs; "
            "the proposal switches it back on"
        )
    if args.fast_check_enabled is not None and FAST_GROUP in cur:
        cur[FAST_GROUP]["enabled"] = args.fast_check_enabled == "true"


def check_proposal(obj):
    """No group running a gate or the digest is off, both gates run, and no placeholder is left."""
    running = set()
    for g, group in obj.items():
        if not isinstance(group, dict):
            continue
        keys = {
            entry_key(ev, e)
            for ev, entries in group.items()
            if isinstance(entries, list)
            for e in entries
        } & {"quality", "review", "digest"}
        if keys and group.get("enabled") is not True:
            raise Refusal(f"the proposal for {HOOKS_JSON} would leave the group {g!r} switched off")
        running |= keys
    if not {"quality", "review"} <= running:
        raise Refusal(f"the proposal for {HOOKS_JSON} would not run both gates")
    text = dump(obj)
    if "{{FAST_CHECK}}" in text or "{{HOOKS_DIR}}" in text:
        raise Refusal(f"the proposal for {HOOKS_JSON} still holds a placeholder")


TOOL_EVENTS = {"PreToolUse", "PostToolUse"}


def malformed(project):
    """Refuse a hooks file in a shape Antigravity rejects. Its schema is mixed: a tool event
    nests its entries as {matcher, hooks: [...]}, every other event is flat {type, command}
    (`docs/verified.md`, `scripts/check-manifests.py`), and one entry of the wrong form makes it
    drop the whole file, so carrying one into a proposal, or calling such a file current, would
    leave every gate off while this script reported success."""

    def refuse(where, what):
        raise Refusal(
            f"{HOOKS_JSON} holds {what} at {where}, and Antigravity rejects the whole file "
            "for one; fix it by hand first"
        )

    for g, group in project.items():
        if not isinstance(group, dict):
            refuse(g, "a group that is not an object")
        for ev, entries in group.items():
            if ev == "enabled":
                continue
            if not isinstance(entries, list):
                refuse(f"{g}.{ev}", "an event whose value is not a list")
            for i, e in enumerate(entries):
                where = f"{g}.{ev}[{i}]"
                if not isinstance(e, dict):
                    refuse(where, "an entry that is not an object")
                inner = e.get("hooks")
                if ev in TOOL_EVENTS:
                    if not (isinstance(inner, list) and all(isinstance(h, dict) for h in inner)):
                        refuse(where, "a tool-event entry without the nested list of hook objects")
                    hooks = inner
                elif "hooks" in e:
                    refuse(where, "a nested entry under an event that takes the flat form")
                else:
                    hooks = [e]
                # The rejection docs/verified.md records: a command hook must specify 'command'.
                for h in hooks:
                    cmd = h.get("command")
                    if not (isinstance(cmd, str) and cmd.strip()):
                        refuse(where, "a hook with no command")


def hooks_plan(root, args, table):
    """The hooks file's state, its proposal, and what must be answered before it is written.

    `blocking` questions need a flag's answer; `asks` are settled by accepting the proposal; an
    edited gate entry also needs --replace .agents/hooks.json."""
    template_text = TEMPLATE.read_text(encoding="utf-8")
    path = root / HOOKS_JSON
    out = {"blocking": [], "asks": [], "notes": [], "needs_replace": False, "old": None}
    if path.is_symlink():
        out.update(state="symlink", target=os.readlink(path))
        return out
    if not os.path.lexists(path):
        if args.fast_check is None:
            out["blocking"].append(
                f"{HOOKS_JSON} is missing: name its fast check with --fast-check"
            )
        out.update(state="missing", proposal=render(template_text, args.fast_check or "true"))
        check_proposal(out["proposal"])
        return out
    try:
        old_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise Refusal(f"{HOOKS_JSON} cannot be read: {e}") from e
    out["old"] = old_text
    try:
        project = json.loads(old_text)
        if not isinstance(project, dict):
            raise ValueError("not an object")
    except ValueError:
        project = None
    if project is not None:
        malformed(project)
    found, why = (
        (None, f"{HOOKS_JSON} is not JSON")
        if project is None
        else identify(project, table["templates"])
    )
    if found is None:
        if args.fast_check is None:
            out["blocking"].append(
                f"{why}, so no value of the project's can be placed in the current shape. "
                "The proposal is the current template; name the fast check with --fast-check"
            )
        cur = render(template_text, args.fast_check or "true")
        for g, group in (project or {}).items():
            if g not in ("gate-sdd", FAST_GROUP):
                cur.setdefault(g, group)
        out.update(state="proposal", proposal=cur, template=None)
        check_proposal(cur)
        return out
    k, tpl, f = found
    fast = f["fast"]
    if args.fast_check is not None:
        fast = args.fast_check
    elif fast is None and f["fast_cmd"] is not None:
        wrapped = [
            h["command"]
            for _s, (_i, e) in slots(render(template_text, f["fast_cmd"])).items()
            if _s[2] == "fast"
            for h in hooks_of(e)
        ]
        out["blocking"].append(
            f"{HOOKS_JSON}: its fast check does not fit the envelope of the template that wrote "
            f"the file, so it cannot be read out of it. Yours: {f['fast_cmd']}  Proposed: "
            f"{wrapped[0] if wrapped else f['fast_cmd']}  Answer with --fast-check <command>"
        )
        fast = f["fast_cmd"]
    elif fast is None:
        fast = "true"
    elif not fast.strip():
        out["notes"].append(f"{HOOKS_JSON}: an empty fast check, rendered as `true`")
        fast = "true"
    cur = render(template_text, fast)
    if f["edited_gates"]:
        out["needs_replace"] = True
        out["asks"].append(
            f"{HOOKS_JSON}: an edited gate entry ({', '.join(sorted(set(f['edited_gates'])))}): "
            "the proposal takes the template's command; "
            f"replace it only with --replace {HOOKS_JSON}"
        )
    for s in f["deleted"]:
        out["asks"].append(
            f"{HOOKS_JSON}: the template's {s[2]} entry in {s[0]}.{s[1]} was deleted; the proposal "
            "restores it (to keep the fast check off, answer --fast-check-enabled false)"
        )
    merge_project_values(cur, project, tpl, f, args, out)
    check_proposal(cur)
    if cur == project and not (out["blocking"] or out["asks"]):
        out.update(state="current")
        return out
    out.update(state="proposal", proposal=cur, template=k)
    return out


def plan_project(root, args, table, current):
    """Everything one project's re-run would do, as a dict the report and the writer read."""
    ag = os.path.lexists(root / HOOKS_JSON) or os.path.lexists(root / HOOKS_DIR)
    contracts = [c for c in table["contract"]["copies"] if os.path.lexists(root / c)]
    guards = [g for g in table["legacy_guards"] if os.path.lexists(root / g)]
    if args.install and not ag:
        ag = True
    if not (ag or contracts or guards):
        return {"no_install": True}
    plan = {
        "no_install": False,
        "copies": [],
        "contracts": [],
        "guards": [],
        "hooks": None,
        "questions": [],
    }
    if ag:
        # A symlinked .agents/ or .agents/hooks/ would take every write somewhere else, so nothing
        # under the link is written: each file under it is reported as a symlink, naming the link.
        link = next((d for d in (".agents", HOOKS_DIR) if (root / d).is_symlink()), None)
        via = f"{link} -> {os.readlink(root / link)}" if link else None
        if link:
            plan["questions"].append(
                f"{link} is a symlink to {os.readlink(root / link)}; nothing is written through it"
            )
        for rel, src in sorted(table["copy_set"].items()):
            cls, detail = classify(root, rel, src, table, current)
            plan["copies"].append(
                (rel, src, "symlink", via) if link and cls != "symlink" else (rel, src, cls, detail)
            )
        plan["hooks"] = (
            {"state": "symlink", "target": via, "blocking": [], "asks": [], "needs_replace": False}
            if link == ".agents"
            else hooks_plan(root, args, table)
        )
    agents_link = (root / ".agents").is_symlink()
    for rel in contracts:
        if agents_link and rel.startswith(".agents/"):
            plan["contracts"].append(
                (
                    rel,
                    table["contract"]["source"],
                    "symlink",
                    f".agents -> {os.readlink(root / '.agents')}",
                )
            )
            continue
        cls, detail = classify(root, rel, table["contract"]["source"], table, current)
        plan["contracts"].append((rel, table["contract"]["source"], cls, detail))
    for rel in guards:
        cls, detail = classify(root, rel, table["legacy_guards"][rel], table, current)
        plan["guards"].append((rel, table["legacy_guards"][rel], cls, detail))
    # The set is judged whole: a kept quality gate that predates the runner stops the checks.
    for rel, _src, cls, detail in plan["copies"]:
        if (
            rel == QUALITY_GATE
            and cls == "edited"
            and rel not in args.replace
            and not runs_the_runner(detail)
        ):
            plan["questions"].append(
                f"{rel} is your edit and does not run harness-checks.sh: kept, the gate stops "
                f"running {', '.join(HARNESS_CHECKS)}. "
                "Keep them on the `- Validators:` line while it stays."
            )
    return plan


def runs_the_runner(text):
    """Whether a quality gate's text calls harness-checks.sh on a line that is not a comment."""
    for line in text.decode("utf-8", errors="replace").splitlines():
        if "harness-checks.sh" in line and not line.lstrip().startswith("#"):
            return True
    return False


def pending(plan, args):
    """The changes this plan proposes, and the questions it leaves, after the answers given."""
    changes, questions, kept = [], list(plan["questions"]), []
    # A pre-0.41.0 guard is outstanding work: #340's migration removes it, so an install that
    # holds one is not current, and a batch names it as behind.
    for rel, _src, cls, detail in plan["guards"]:
        ask = ", and asks first because it is your edit" if cls == "edited" else ""
        if cls == "symlink":
            ask = f", and asks first: it is a symlink to {detail}"
        questions.append(
            f"{rel} is a pre-0.41.0 guard ({cls}): init's guard migration (#340) removes it{ask}"
        )
    for rel, src, cls, _detail in plan["copies"] + plan["contracts"]:
        if cls in ("shipped", "missing"):
            changes.append((rel, src))
        elif cls == "edited":
            if rel in args.replace:
                changes.append((rel, src))
            else:
                kept.append(rel)
                questions.append(f"{rel} is your edit: it is replaced only with --replace {rel}")
        elif cls == "symlink":
            questions.append(f"{rel} is a symlink to {_detail}; nothing is written through it")
    h = plan["hooks"]
    hooks_write = False
    if h and h["state"] == "symlink":
        questions.append(
            f"{HOOKS_JSON} is a symlink to {h['target']}; nothing is written through it"
        )
    elif h and h["state"] != "current":
        replaced = not h["needs_replace"] or HOOKS_JSON in args.replace
        accepted = args.hooks_json or (h["state"] == "missing" and args.install)
        if accepted and not h["blocking"] and replaced:
            hooks_write = True
        else:
            questions.extend(h["blocking"] + h["asks"])
            if not accepted and not h["blocking"]:
                questions.append(f"{HOOKS_JSON} has a proposal: accept it with --hooks-json")
    return changes, questions, kept, hooks_write


def write_file(root, rel, data, mode):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.lexists(tmp):
            os.unlink(tmp)
        raise


def apply(root, plan, args):
    changes, questions, kept, hooks_write = pending(plan, args)
    h = plan["hooks"]
    copy_changes = [c for c in changes if c[0].startswith(HOOKS_DIR + "/")]
    hooks_current_after = h is None or h["state"] == "current" or hooks_write
    if copy_changes and not hooks_current_after:
        if h["state"] == "symlink":
            why = (
                f"{HOOKS_JSON} is a symlink to {h['target']}, and nothing is written through it, "
                "so the gates are not refreshed without it. "
                "Replace the link with a file and run again."
            )
        else:
            why = (
                f"{HOOKS_JSON} would stay older than the gates. "
                "Accept its proposal with --hooks-json, or answer its question, and run again."
            )
        print(f"upgrade-install: nothing written: {why}")
        for q in questions:
            print(f"  question {q}")
        return EXIT_PENDING
    writes = [(rel, (PLUGIN / src).read_bytes(), PLUGIN / src) for rel, src in changes]
    if hooks_write:
        writes.append((HOOKS_JSON, dump(h["proposal"]).encode("utf-8"), None))
    # Every destination is checked before any file is written, so a directory that refuses a
    # write stops the run with nothing written. A write can still fail later, as a sandbox that
    # refuses the temporary file does; that exits 1 and names what was already written.
    for rel, _data, _source in writes:
        d = (root / rel).parent
        while not d.exists() and d != root:
            d = d.parent
        if not os.access(d, os.W_OK):
            print(
                f"upgrade-install: refused: {d.relative_to(root)} cannot be written, "
                "so nothing was written.",
                file=sys.stderr,
            )
            return EXIT_REFUSED
    done = []
    for rel, data, source in writes:
        dest = root / rel
        try:
            if dest.is_file():
                mode = dest.stat().st_mode & 0o7777
            else:
                mode = source.stat().st_mode & 0o7777 if source else 0o644
            write_file(root, rel, data, mode)
        except OSError as e:
            print(
                f"upgrade-install: write failed at {rel}: {e}. "
                f"Already written: {', '.join(done) or 'nothing'}.",
                file=sys.stderr,
            )
            return EXIT_REFUSED
        done.append(rel)
    for rel in done:
        print(f"  wrote    {rel}")
    for q in questions:
        print(f"  question {q}")
    remaining = questions
    if kept or remaining:
        print(
            f"upgrade-install: applied {len(done)}; {len(kept)} edit(s) kept, set mixed"
            if kept
            else f"upgrade-install: applied {len(done)}; {len(remaining)} question(s) left"
        )
        return EXIT_PENDING
    print(f"upgrade-install: applied {len(done)} change(s)")
    return EXIT_OK


def report(root, plan, args):
    print(f"upgrade-install: project {root}")
    if plan["no_install"]:
        print("upgrade-install: no install")
        return EXIT_NO_INSTALL
    notes = {
        "current": "",
        "shipped": "an earlier text of this plugin; replaced on --write",
        "missing": "added on --write",
        "symlink": "a symlink to {detail}; nothing is written through it",
    }
    for rel, src, cls, detail in plan["copies"] + plan["contracts"]:
        if cls == "edited":
            print(f"  edited   {rel}  (your edit; replaced only with --replace {rel})")
            cur = (
                (PLUGIN / src)
                .read_text(encoding="utf-8", errors="replace")
                .splitlines(keepends=True)
            )
            mine = detail.decode("utf-8", errors="replace").splitlines(keepends=True)
            sys.stdout.writelines(
                difflib.unified_diff(mine, cur, f"{rel} (yours)", f"{rel} (plugin)")
            )
        else:
            note = notes[cls].format(detail=detail) if cls == "symlink" else notes[cls]
            print(f"  {cls:<8} {rel}" + (f"  ({note})" if note else ""))
    for rel, src, cls, detail in plan["guards"]:
        print(
            f"  guard    {rel}: {cls}"
            + (f" to {detail}" if cls == "symlink" else "")
            + "; #340's migration removes it, and this script never writes it"
        )
        if cls == "edited":
            cur = (PLUGIN / src).read_text(encoding="utf-8", errors="replace")
            mine = detail.decode("utf-8", errors="replace")
            sys.stdout.writelines(
                difflib.unified_diff(
                    mine.splitlines(keepends=True),
                    cur.splitlines(keepends=True),
                    f"{rel} (yours)",
                    f"{rel} (plugin)",
                )
            )
    h = plan["hooks"]
    if h:
        if h["state"] == "current":
            print(f"  current  {HOOKS_JSON}")
        elif "proposal" in h:
            if h["state"] == "missing":
                origin = "missing"
            elif h.get("template"):
                origin = f"written by the template {h['template'][:12]}"
            else:
                origin = "no template identified"
            print(f"  proposed {HOOKS_JSON}  ({origin}; accept with --hooks-json)")
            for note in h["notes"]:
                print(f"  note     {note}")
            old = (h.get("old") or "").splitlines(keepends=True)
            sys.stdout.writelines(
                difflib.unified_diff(
                    old,
                    dump(h["proposal"]).splitlines(keepends=True),
                    f"{HOOKS_JSON} (yours)",
                    f"{HOOKS_JSON} (proposed)",
                )
            )
    changes, questions, kept, _hooks_write = pending(plan, args)
    for q in questions:
        print(f"  question {q}")
    n_changes = len(changes) + (1 if (h and h["state"] != "current" and "proposal" in h) else 0)
    if not n_changes and not questions:
        print("upgrade-install: nothing to upgrade")
        return EXIT_OK
    if kept and not changes and len(questions) == len(kept):
        print(f"upgrade-install: {len(kept)} edit(s) kept, set mixed")
    else:
        print(f"upgrade-install: {n_changes} change(s) proposed, {len(questions)} question(s)")
    return EXIT_PENDING


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--project",
        action="append",
        required=True,
        help="a project directory; repeat for a batch report",
    )
    ap.add_argument(
        "--write", action="store_true", help="apply what the report proposes and the answers allow"
    )
    ap.add_argument(
        "--replace",
        action="append",
        default=[],
        help="replace this edited file (a project-relative path)",
    )
    ap.add_argument(
        "--hooks-json", action="store_true", help="accept the proposal for .agents/hooks.json"
    )
    ap.add_argument("--fast-check", help="the fast check command the hooks file runs")
    ap.add_argument(
        "--fast-check-enabled", choices=("true", "false"), help="the fast-check group's `enabled`"
    )
    ap.add_argument(
        "--install", action="store_true", help="make an Antigravity install where there is none"
    )
    args = ap.parse_args()
    try:
        table, current = load_table()
    except Refusal as e:
        print(f"upgrade-install: refused: {e}", file=sys.stderr)
        return EXIT_REFUSED
    if args.write and len(args.project) > 1:
        print("upgrade-install: refused: --write takes exactly one --project", file=sys.stderr)
        return EXIT_REFUSED
    codes, behind, refused = [], [], []
    for p in args.project:
        try:
            root = project_root(p)
            plan = plan_project(root, args, table, current)
            if args.write and not plan["no_install"]:
                code = apply(root, plan, args)
            else:
                code = report(root, plan, args)
        except Refusal as e:
            print(f"upgrade-install: refused: {p}: {e}", file=sys.stderr)
            code = EXIT_REFUSED
        codes.append(code)
        (refused if code == EXIT_REFUSED else behind if code == EXIT_PENDING else []).append(p)
    if len(args.project) > 1:
        print(
            f"upgrade-install: {len(args.project)} project(s): "
            f"behind: {', '.join(behind) or 'none'}; "
            f"refused: {', '.join(refused) or 'none'}"
        )
    return min(codes, key=WORST.index)


if __name__ == "__main__":
    sys.exit(main())
