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


def fast_commands(template_obj):
    """(group, event, entry index, hook index) of every command that holds {{FAST_CHECK}}."""
    sites = []
    for g, group in template_obj.items():
        for ev, entries in group.items():
            if not isinstance(entries, list):
                continue
            for i, e in enumerate(entries):
                for j, h in enumerate(e.get("hooks", [e])):
                    if "{{FAST_CHECK}}" in h.get("command", ""):
                        sites.append((g, ev, i, j))
    return sites


def at(obj, site):
    g, ev, i, j = site
    e = obj[g][ev][i]
    return e["hooks"][j] if "hooks" in e else e


def capture_fast(template_obj, project_obj):
    """The project's fast check, read through the template's envelope, or None."""
    for site in fast_commands(template_obj):
        try:
            pattern, cmd = at(template_obj, site)["command"], at(project_obj, site)["command"]
        except (KeyError, IndexError, TypeError):
            return None
        pattern = pattern.replace("{{HOOKS_DIR}}", HOOKS_DIR)
        head, _, tail = pattern.partition("{{FAST_CHECK}}")
        m = re.fullmatch(re.escape(head) + "(.*)" + re.escape(tail), cmd, re.S)
        if not m:
            return None
        return m.group(1)
    return None


def hooks_plan(root, args):
    """The hooks file's state: a dict with state, proposal and questions."""
    template_text = TEMPLATE.read_text(encoding="utf-8")
    path = root / HOOKS_JSON
    if path.is_symlink():
        return {
            "state": "question",
            "questions": [
                f"{HOOKS_JSON} is a symlink to {os.readlink(path)}; nothing is written through it"
            ],
        }
    if not os.path.lexists(path):
        fast = args.fast_check if args.fast_check is not None else "true"
        q = (
            []
            if args.fast_check is not None
            else [
                f"{HOOKS_JSON} is missing and no --fast-check was given: the proposal runs `true`"
            ]
        )
        return {
            "state": "missing",
            "proposal": render(template_text, fast),
            "old": None,
            "questions": q,
        }
    try:
        old_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise Refusal(f"{HOOKS_JSON} cannot be read: {e}") from e
    try:
        project = json.loads(old_text)
    except ValueError:
        return {
            "state": "question",
            "old": old_text,
            "proposal": render(template_text, args.fast_check or "true"),
            "questions": [
                f"{HOOKS_JSON} is not JSON, so no value of the project's can be read from it"
            ],
        }
    template = json.loads(template_text)
    fast = capture_fast(template, project)
    if fast is not None and render(template_text, fast) == project:
        return {"state": "current"}
    return {
        "state": "question",
        "old": old_text,
        "proposal": render(template_text, args.fast_check or fast or "true"),
        "questions": [
            f"{HOOKS_JSON} is not in the current template's shape, "
            "and this version reads no other shape"
        ],
    }


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
        dir_link = (root / HOOKS_DIR).is_symlink()
        if dir_link:
            plan["questions"].append(
                f"{HOOKS_DIR} is a symlink to {os.readlink(root / HOOKS_DIR)}; "
                "nothing is written through it"
            )
        for rel, src in sorted(table["copy_set"].items()):
            cls, detail = classify(root, rel, src, table, current)
            plan["copies"].append(
                (rel, src, "symlink" if dir_link and cls != "symlink" else cls, detail)
            )
        plan["hooks"] = hooks_plan(root, args)
    for rel in contracts:
        cls, detail = classify(root, rel, table["contract"]["source"], table, current)
        plan["contracts"].append((rel, table["contract"]["source"], cls, detail))
    for rel in guards:
        cls, detail = classify(root, rel, table["legacy_guards"][rel], table, current)
        plan["guards"].append((rel, cls))
    # The set is judged whole: a kept quality gate that predates the runner stops the checks.
    for rel, _src, cls, detail in plan["copies"]:
        if (
            rel == QUALITY_GATE
            and cls == "edited"
            and rel not in args.replace
            and b"harness-checks.sh" not in detail
        ):
            plan["questions"].append(
                f"{rel} is your edit and does not run harness-checks.sh: kept, the gate stops "
                f"running {', '.join(HARNESS_CHECKS)}. "
                "Keep them on the `- Validators:` line while it stays."
            )
    return plan


def pending(plan, args):
    """The changes this plan proposes, and the questions it leaves, after the answers given."""
    changes, questions, kept = [], list(plan["questions"]), []
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
            questions.append(f"{rel} is a symlink; nothing is written through it")
    h = plan["hooks"]
    hooks_write = False
    if h and h["state"] != "current":
        accepted = args.hooks_json and "proposal" in h
        if accepted or (h["state"] == "missing" and args.install):
            hooks_write = True
        else:
            questions.extend(
                h["questions"] or [f"{HOOKS_JSON} has a proposal: accept it with --hooks-json"]
            )
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
        print(
            f"upgrade-install: nothing written: {HOOKS_JSON} would stay older than the gates. "
            "Accept its proposal with --hooks-json, or answer its question, and run again."
        )
        return EXIT_PENDING
    writes = [(rel, (PLUGIN / src).read_bytes(), PLUGIN / src) for rel, src in changes]
    if hooks_write:
        writes.append((HOOKS_JSON, dump(h["proposal"]).encode("utf-8"), None))
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
        "symlink": "a symlink; nothing is written through it",
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
            note = notes[cls]
            print(f"  {cls:<8} {rel}" + (f"  ({note})" if note else ""))
    for rel, cls in plan["guards"]:
        print(
            f"  guard    {rel}: {cls}; #340's migration removes it, and this script never writes it"
        )
    h = plan["hooks"]
    if h:
        if h["state"] == "current":
            print(f"  current  {HOOKS_JSON}")
        elif "proposal" in h:
            print(f"  proposed {HOOKS_JSON}  (accept with --hooks-json)")
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
