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


def check_categories(rel_path: str, policy: str) -> list[str]:
    """Verify that all four sanctioned categories are present in the reviewer's Bash policy.

    Sanctioned categories from reviewer-contract.md:
    1. diff/log/commit
    2. clock (date -u)
    3. installed version check (package manager, environment listing, SDK version, or reasoned N/A)
    4. validators (named in .steering/tech.md or enumerated list)
    """
    errors: list[str] = []

    # 1. diff/log/commit
    has_diff = bool(re.search(r"\bgit\s+(diff|log|rev-parse)\b", policy))
    if not has_diff:
        errors.append(f"{rel_path} is missing category 'diff/log/commit'")

    # 2. clock
    has_clock = bool(re.search(r"\bdate\s+-u\b", policy))
    if not has_clock:
        errors.append(f"{rel_path} is missing category 'clock'")

    # 3. installed version
    # Check for N/A declaration
    cat3_na_lines = [
        line for line in policy.splitlines()
        if re.search(r"\b(?:n/a|not applicable)\b", line, re.IGNORECASE)
        and re.search(r"version|package|sdk|dependency|category\s*3", line, re.IGNORECASE)
    ]
    if cat3_na_lines:
        has_reason = False
        for line in cat3_na_lines:
            m_paren = re.search(r"\b(?:n/a|not applicable)\b\s*\(([^)]+)\)", line, re.IGNORECASE)
            m_sep = re.search(r"\b(?:n/a|not applicable)\b\s*[-—:,]\s*(\S+.*)", line, re.IGNORECASE)
            if (m_paren and m_paren.group(1).strip()) or (m_sep and m_sep.group(1).strip()):
                has_reason = True
                break
        if not has_reason:
            errors.append(f"{rel_path} declares category 'installed version' N/A without a stated reason")
    else:
        has_cat3 = bool(re.search(r"package\s+manager|package\s+listing|sdk\s+version", policy, re.IGNORECASE))
        if not has_cat3:
            errors.append(f"{rel_path} is missing category 'installed version'")

    # 4. validators
    has_validators = bool(re.search(r"\bvalidators\b", policy, re.IGNORECASE))
    if not has_validators:
        errors.append(f"{rel_path} is missing category 'validators'")

    return errors


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

    # Categories check across all REVIEWERS
    category_errors: list[str] = []
    for rel in REVIEWERS:
        reviewer_file = ROOT / rel
        if not reviewer_file.is_file():
            print(f"check-reviewer-allow-list FAILED — reviewer {rel} does not exist", file=sys.stderr)
            sys.exit(1)
        r_policy = bash_policy(reviewer_file)
        if r_policy is None:
            print(f"check-reviewer-allow-list FAILED — {rel} has no '## Bash policy' section", file=sys.stderr)
            sys.exit(1)
        category_errors.extend(check_categories(rel, r_policy))

    if category_errors:
        for err in category_errors:
            print(f"check-reviewer-allow-list FAILED — {err}", file=sys.stderr)
        sys.exit(1)

    print(f"check-reviewer-allow-list: {len(validators)} validator(s) covered in {DOGFOOD}; all {len(REVIEWERS)} reviewer(s) satisfy categories")


if __name__ == "__main__":
    main()
