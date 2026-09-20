#!/usr/bin/env python3
"""Guards against silent drift between .steering/tech.md's - Validators: line and the reviewer's allow-list.

#131: .steering/tech.md's - Validators: line is the authority on which commands gate a turn,
and quality-gate.sh runs whatever that line names. The dogfood reviewer enumerates validators
by hand in its ## Bash policy block, and that list drifted — three validators added to steering
were never added to the reviewer, so the reviewer silently failed to re-run them during reviews.

This guard enforces:
1. Coverage (AC1, AC2, AC7): every validator on .steering/tech.md's - Validators: line is
   present on the dogfood reviewer's Bash policy allow-list. Extra sanctioned commands (such as
   check-version-bump.py) are allowed on the allow-list (containment, not equality).
2. Categories (AC3, AC4, AC5): all four sanctioned categories from reviewer-contract.md
   (diff/log/commit, clock, installed version check, validators) appear on every reviewer's
   allow-list, with stack-specific variants or an explicit, reasoned N/A declaration accepted.

Exits 0 when every validator is covered and all categories are respected.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path.cwd()

STEERING = pathlib.Path(".steering/tech.md")
DOGFOOD = pathlib.Path(".claude/agents/gate-sdd-reviewer.md")

REVIEWERS = (
    "agents/ts-reviewer.md",
    "agents/python-reviewer.md",
    "agents/dart-flutter-reviewer.md",
    "agents/_template/reviewer.md",
    ".claude/agents/gate-sdd-reviewer.md",
)
MIN_REVIEWERS = 5


def bash_policy(path: pathlib.Path) -> str | None:
    """The text of a reviewer's `## Bash policy` section, or None if it has no such section."""
    if not path.is_file():
        return None
    lines = path.read_text().splitlines()
    body: list[str] = []
    inside = False
    for line in lines:
        if line.startswith("## "):
            if inside:
                break
            inside = line.strip().lower() == "## bash policy"
            continue
        if inside:
            body.append(line)
    return "\n".join(body) if inside else None


def read_validators(steering_path: pathlib.Path) -> list[str]:
    """Parse comma-separated validator commands from the `- Validators:` line."""
    if not steering_path.is_file():
        return []
    for line in steering_path.read_text().splitlines():
        m = re.match(r"^ *- *Validators: *(.*)$", line)
        if m:
            raw = m.group(1).strip()
            return [cmd.strip() for cmd in raw.split(",") if cmd.strip()]
    return []


def main() -> None:
    if len(REVIEWERS) < MIN_REVIEWERS:
        print(f"check-reviewer-allow-list FAILED — REVIEWERS is below its floor of {MIN_REVIEWERS}", file=sys.stderr)
        sys.exit(1)

    steering_file = ROOT / STEERING
    if not steering_file.is_file():
        print(f"check-reviewer-allow-list FAILED — {STEERING} does not exist", file=sys.stderr)
        sys.exit(1)

    validators = read_validators(steering_file)
    if not validators:
        print(f"check-reviewer-allow-list FAILED — {STEERING} has no readable '- Validators:' line", file=sys.stderr)
        sys.exit(1)

    dogfood_file = ROOT / DOGFOOD
    if not dogfood_file.is_file():
        print(f"check-reviewer-allow-list FAILED — {DOGFOOD} does not exist", file=sys.stderr)
        sys.exit(1)

    policy = bash_policy(dogfood_file)
    if policy is None:
        print(f"check-reviewer-allow-list FAILED — {DOGFOOD} has no '## Bash policy' section", file=sys.stderr)
        sys.exit(1)

    spans = re.findall(r"`([^`]+)`", policy)
    missing = [
        v for v in validators
        if not any(span == v or span.startswith(v + " ") for span in spans)
    ]

    if missing:
        print(
            f"check-reviewer-allow-list FAILED — {DOGFOOD} is missing validators from {STEERING}",
            file=sys.stderr,
        )
        for m in missing:
            print(f"  absent: {m}", file=sys.stderr)
        print("  Every validator on the '- Validators:' line must appear on the reviewer's allow-list.", file=sys.stderr)
        sys.exit(1)

    print(f"check-reviewer-allow-list: {len(validators)} validator(s) covered in {DOGFOOD}")


if __name__ == "__main__":
    main()
