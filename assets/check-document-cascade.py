#!/usr/bin/env python3
"""Verify the document cascade against the latest commit modifying PRD.md.

Downstream inception documents (DESIGN.md, BACKLOG.md, and under full mode ROADMAP.md and
CONTRACT.md) must declare `- Reconciled against PRD: <sha>` on one physical line matching
the latest git commit SHA modifying PRD.md.

Serves CAP-6 (LV-4) — Planning that terminates in something the harness reads.
Establishes the mechanical terminus for the planning chain:
  prd -> design-doc / roadmap / backlog / contract

Run from the repository root. Exits 0 when downstream documents are reconciled against PRD.md.
"""

import pathlib
import re
import subprocess
import sys

STEERING = pathlib.Path(".steering/tech.md")
MODES = ("bootstrap", "minimum", "full")
DOWNSTREAM_MINIMUM = ("DESIGN.md", "BACKLOG.md")
DOWNSTREAM_FULL = ("DESIGN.md", "BACKLOG.md", "ROADMAP.md", "CONTRACT.md")


def fail(message):
    print(f"check-document-cascade: {message}", file=sys.stderr)
    raise SystemExit(1)


def steering_value(text, key):
    """The first value for `key`, byte-for-byte as `gate_steering_value` would return it."""
    for line in text.split("\n"):
        m = re.match(rf"^ *- *{key}: *(.*)$", line)
        if m:
            return m.group(1)
    return ""


def main():
    if not STEERING.is_file():
        fail(f"{STEERING} does not exist, so no mode is declared and nothing can be verified.")
    try:
        text = STEERING.read_text()
    except OSError as exc:
        fail(f"{STEERING} cannot be read ({exc.strerror}), so the declared mode is unknown.")

    mode = steering_value(text, "Mode")
    if not mode:
        fail(
            f"{STEERING} carries no readable `- Mode:` line. Add one of "
            f"{', '.join(f'`- Mode: {m}`' for m in MODES)} on one physical line. "
            f"A mode is declared, never assumed."
        )
    if mode not in MODES:
        if mode.strip() in MODES:
            fail(
                f"`- Mode:` carries trailing whitespace, so its value is {mode!r} rather than "
                f"{mode.strip()!r}. Remove the trailing space."
            )
        fail(f"`- Mode: {mode}` is not a mode. Expected one of: {', '.join(MODES)}.")

    if mode == "bootstrap":
        print(
            "check-document-cascade: mode `bootstrap` — inception documents not yet authored; "
            "cascade verification deferred"
        )
        return

    docs_value = steering_value(text, "Docs").strip() or "docs/"
    if "://" in docs_value:
        fail(
            f"`- Docs: {docs_value}` names another repository, so the document cascade "
            "cannot be verified from here. Remove this checker from `- Validators:` for a "
            "multi-repo install, or point `- Docs:` at a local directory."
        )

    docs = pathlib.Path(docs_value)
    if not docs.is_dir():
        fail(f"`- Docs: {docs_value}` does not name a directory that exists.")

    prd_path = docs / "PRD.md"
    if not prd_path.is_file():
        fail(f"{prd_path} does not exist; cascade cannot be established.")

    try:
        res_status = subprocess.run(
            ["git", "status", "--porcelain", "--", str(prd_path)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        fail(f"git command failed ({exc}): cannot establish repository status.")

    if res_status.returncode != 0:
        fail(f"git status failed on {prd_path}: {res_status.stderr.strip()}")
    if res_status.stdout.strip():
        fail(
            f"{prd_path} has uncommitted working tree changes; "
            f"commit {prd_path} before reconciling downstream documents."
        )

    try:
        res_log = subprocess.run(
            ["git", "log", "-n", "1", "--format=%H", "--", str(prd_path)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        fail(f"git command failed ({exc}): cannot establish commit history.")

    if res_log.returncode != 0:
        fail(f"cannot establish git history for {prd_path}: {res_log.stderr.strip()}")
    prd_sha = res_log.stdout.strip()
    if not re.match(r"^[0-9a-fA-F]{40}$", prd_sha):
        fail(f"cannot determine commit SHA for {prd_path}; git returned {prd_sha!r}.")

    required_names = DOWNSTREAM_MINIMUM if mode == "minimum" else DOWNSTREAM_FULL
    failures = []

    for name in required_names:
        doc_path = docs / name
        if not doc_path.is_file():
            failures.append(f"{doc_path} does not exist")
            continue
        try:
            doc_text = doc_path.read_text()
        except OSError as exc:
            failures.append(f"{doc_path} cannot be read ({exc.strerror})")
            continue

        lines = [
            line
            for line in doc_text.splitlines()
            if re.match(r"^ *- *Reconciled against PRD:", line)
        ]
        if not lines:
            failures.append(f"{doc_path} is missing `- Reconciled against PRD:` declaration")
            continue
        if len(lines) > 1:
            failures.append(
                f"{doc_path} carries multiple `- Reconciled against PRD:` declarations "
                f"({len(lines)})"
            )
            continue

        m = re.match(r"^ *- *Reconciled against PRD: *(.*)$", lines[0])
        sha_val = m.group(1).strip() if m else ""
        if not re.match(r"^[0-9a-fA-F]{40}$", sha_val):
            failures.append(
                f"{doc_path} carries malformed reconciliation SHA {sha_val!r}; "
                f"expected 40-character hex commit SHA"
            )
            continue

        if sha_val.lower() != prd_sha.lower():
            failures.append(
                f"{doc_path} is reconciled against {sha_val}, but {prd_path} is at {prd_sha}"
            )

    if failures:
        fail(
            f"document cascade verification failed on {len(failures)} item(s):\n  "
            + "\n  ".join(failures)
        )

    print(
        f"check-document-cascade: mode `{mode}` at `{docs}/` — {len(required_names)} "
        f"downstream document(s) reconciled against {prd_path.name} ({prd_sha[:8]})"
    )


if __name__ == "__main__":
    main()
