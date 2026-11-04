#!/usr/bin/env python3
"""Build, or check, assets/shipped-texts.json: every text each copied file has had on main (#343).

A re-run of `init` on an Antigravity project reads this table to tell a copy the plugin wrote,
which it may replace, from one the project edited, which it must ask about (#343's C2). A copy
carries no version, and tags miss shipped states, so the table holds every text, by sha256, that
each copied file's source has had at a first-parent commit of the default branch, plus the
working tree's current text. A commit only a feature branch held was never the default branch, so
it is never in the table, and a branch's table is the same at its tip and at its merge.

The history is the first-parent chain of the merge-base of HEAD and the base ref (`origin/main`
unless `--base` names another). In CI's pull-request checkout HEAD is the merge commit and the
base is the pull request's base, so the merge-base is the base and the working tree is the merged
tree; on a branch it is the branch point and the branch's tip. Either way the table is the
history's texts plus the tree's.

The table's hand-kept keys are read, never written:
  copy_set        each file `init` copies into .agents/hooks/, to its source in the plugin
  contract        the reviewer contract's source, and where `init` copies it
  aliases         a source's earlier paths, so its history follows a move
  legacy_guards   a pre-0.41.0 install's scripts/ guards, to their sources
  templates_from  the commit from which the Antigravity hooks template's texts count (v0.2.3)
The builder derives the rest:
  texts           each source path to the sorted sha256 of every text it has had
  templates       each Antigravity hooks template text since templates_from, by its sha256

Without --check it writes the table. With --check it writes nothing and exits 1 when the table is
not exactly what it would write, naming the file and the remedy. Where the history cannot be read
(no base ref, or a shallow clone) --check says the history check was skipped and why, and still
checks that every current text is in the table; a build refuses, because it cannot see the history.
It is not shipped: it needs the plugin's own git history, which an install does not have.
"""

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

TABLE = "assets/shipped-texts.json"
TEMPLATE = "hooks/templates/antigravity.hooks.json"
DERIVED = ("texts", "templates")


def git(repo, *args, stdin=None):
    r = subprocess.run(["git", "-C", str(repo), *args], input=stdin, capture_output=True)
    return r.returncode, r.stdout


def fail(msg):
    print(f"build-shipped-texts: {msg}", file=sys.stderr)
    sys.exit(1)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def history(repo, base):
    """First-parent commits of merge-base(HEAD, base), or (None, why) when they cannot be read."""
    rc, out = git(repo, "rev-parse", "--is-shallow-repository")
    if rc != 0:
        return None, f"cannot ask git whether {repo} is shallow"
    if out.strip() == b"true":
        return None, f"{repo} is a shallow clone, so its history is incomplete"
    rc, _ = git(repo, "rev-parse", "-q", "--verify", f"{base}^{{commit}}")
    if rc != 0:
        return None, f"no {base} in {repo}, so there is no default branch to read the history of"
    rc, out = git(repo, "merge-base", "HEAD", base)
    if rc != 0:
        return None, f"HEAD and {base} share no history in {repo}"
    mb = out.decode().strip()
    rc, out = git(repo, "rev-list", "--first-parent", mb)
    if rc != 0:
        return None, f"cannot list the first-parent history of {mb[:12]}"
    return out.decode().split(), None


def blobs_at(repo, commits, path):
    """The distinct blob ids `path` has at `commits`."""
    if not commits:
        return set()
    query = "".join(f"{c}:{path}\n" for c in commits).encode()
    rc, out = git(repo, "cat-file", "--batch-check", stdin=query)
    if rc != 0:
        fail(f"git cat-file failed reading {path}'s history")
    ids = set()
    for line in out.decode().splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "blob":
            ids.add(parts[0])
    return ids


def blob_bytes(repo, blob):
    rc, out = git(repo, "cat-file", "blob", blob)
    if rc != 0:
        fail(f"git cat-file cannot read blob {blob}")
    return out


def hand_keys(table):
    for key in ("copy_set", "contract", "aliases", "legacy_guards", "templates_from"):
        if key not in table:
            fail(f"{TABLE} has no `{key}`, which is kept by hand; restore it before building")
    sources = set(table["copy_set"].values()) | {table["contract"]["source"]} | set(table["legacy_guards"].values())
    return sorted(sources)


def build(repo, table, commits):
    """The derived keys: from `commits` when given, and always from the working tree."""
    sources = hand_keys(table)
    texts = {}
    for src in sources:
        f = repo / src
        if not f.is_file():
            fail(f"{src} is named in {TABLE} and is not a file in {repo}")
        hashes = {sha(f.read_bytes())}
        if commits is not None:
            for path in [src, *table["aliases"].get(src, [])]:
                hashes |= {sha(blob_bytes(repo, b)) for b in blobs_at(repo, commits, path)}
        texts[src] = sorted(hashes)
    tpl = repo / TEMPLATE
    if not tpl.is_file():
        fail(f"{TEMPLATE} is not a file in {repo}")
    templates = {sha(tpl.read_bytes()): tpl.read_bytes().decode("utf-8")}
    if commits is not None:
        cut = table["templates_from"]
        since = [c for c in commits if git(repo, "merge-base", "--is-ancestor", cut, c)[0] == 0]
        for b in blobs_at(repo, since, TEMPLATE):
            data = blob_bytes(repo, b)
            templates[sha(data)] = data.decode("utf-8")
    return {"texts": texts, "templates": dict(sorted(templates.items()))}


def write(repo, table, derived):
    out = {k: v for k, v in table.items() if k not in DERIVED}
    out.update(derived)
    text = json.dumps(out, indent=1, sort_keys=True, ensure_ascii=True) + "\n"
    (repo / TABLE).write_text(text, encoding="utf-8")


def check(table, derived, partial, base):
    """Each problem as a sentence naming the file and the remedy."""
    rebuild = "run `python3 scripts/build-shipped-texts.py` and commit the table"
    problems = []
    have = {**{k: set(v) for k, v in table.get("texts", {}).items()}, TEMPLATE: set(table.get("templates", {}))}
    want = {**{k: set(v) for k, v in derived["texts"].items()}, TEMPLATE: set(derived["templates"])}
    for src in sorted(want):
        got = have.get(src, set())
        missing, extra = want[src] - got, got - want[src]
        if partial:
            # Only the working tree's text is known, and it is the one the build put first.
            current = missing
            if current:
                problems.append(f"{src}'s current text is not in {TABLE}: {rebuild}")
            continue
        if missing:
            problems.append(
                f"{src} has {len(missing)} text(s) on {base}'s first-parent history or in the working tree "
                f"that {TABLE} lacks: merge the default branch if it moved, then {rebuild}"
            )
        if extra:
            problems.append(
                f"{src}: {TABLE} holds {len(extra)} text(s) neither {base}'s first-parent history nor "
                f"the working tree has ({', '.join(sorted(e[:12] for e in extra))}): {rebuild}"
            )
    for src in sorted(set(have) - set(want)):
        problems.append(f"{TABLE} holds texts for {src}, which no hand-kept key names: {rebuild}")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if the table is stale")
    ap.add_argument("--base", default="origin/main", help="the default branch's ref (default origin/main)")
    args = ap.parse_args()

    rc, out = git(pathlib.Path.cwd(), "rev-parse", "--show-toplevel")
    if rc != 0:
        fail("not inside a git repository, so there is no history to read")
    repo = pathlib.Path(out.decode().strip())
    path = repo / TABLE
    try:
        table = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"{TABLE} does not exist; its hand-kept keys must be written first")
    except (OSError, ValueError) as e:
        fail(f"{TABLE} cannot be read as JSON: {e}")

    commits, why = history(repo, args.base)
    if args.check:
        derived = build(repo, table, commits)
        if why:
            print(f"build-shipped-texts: history check skipped: {why}")
        problems = check(table, derived, partial=why is not None, base=args.base)
        for p in problems:
            print(f"build-shipped-texts: {p}", file=sys.stderr)
        if problems:
            sys.exit(1)
        n = sum(len(v) for v in derived["texts"].values())
        scope = "current texts" if why else f"{n} text(s) and {len(derived['templates'])} template(s)"
        print(f"build-shipped-texts: {TABLE} holds every {scope} it should")
        return
    if why:
        fail(f"cannot build: {why}")
    derived = build(repo, table, commits)
    write(repo, table, derived)
    n = sum(len(v) for v in derived["texts"].values())
    print(f"build-shipped-texts: wrote {TABLE}: {n} text(s) over {len(derived['texts'])} source(s), "
          f"{len(derived['templates'])} template(s), from {len(commits)} first-parent commit(s)")


if __name__ == "__main__":
    main()
