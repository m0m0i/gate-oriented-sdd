# Observations — 141-init-asks-for-the-target-document-set

## Review round 1 — CLEAN, 0 blockers, 0 HIGH, 4 MEDIUM, 5 LOW

Reviewed at `a6f464252955547cd8ca479af3111c2e3e589c0d` by `gate-sdd-reviewer`, `reviewed_by=subagent`.

The reviewer verified C1 in the code rather than accepting it from the spec, which is the check that mattered: `wanted` is built from `mode` alone, `target` appears in no path that decides an exit code, and the diff removes no exit-1 path while adding exactly one (AC9). A mistyped or absent target therefore cannot turn a red run green. That is the anchor — gates never fail open — applied to the one design decision this spec turned on.

## What is verified, and what is only pinned

This is the entry the reviewer asked for, and it exists because three criteria describe what a **model** does when running `init`, and `test-gates.sh` cannot observe that. It can observe only that the instruction is present and that deleting it fails a guard. Without this note those three read as verified when they are pinned-but-unobserved.

| AC | Status | Evidence |
| :-- | :-- | :-- |
| AC1 | **not exercised** — pinned by contract, no `init` run | `skills/init/SKILL.md:40`, pinned `scripts/check-skill-contracts.py`, case 74 |
| AC2 | **not exercised** — pinned by contract, no `init` run | `skills/init/SKILL.md:40,50`, both pins, case 74 |
| AC3 | verified | `assets/check-document-set.py` bootstrap branch, case 71 |
| AC4 | verified | case 71 control (no target keeps today's wording) + case 72 empty-value half |
| AC5 | verified | case 72 `spent-unread`, `spent-bogus-unread` |
| AC6 | **not exercised** — pre-existing pin, no `init` run | existing upgrade entry in `check-skill-contracts.py`, case 69 `noupgrade` |
| AC7 | verified | question and destination both pinned, case 74 both halves |
| AC8 | verified | case 73, including the units-stay-separate halves |
| AC9 | verified | case 72 `bogus-red`, `names-value` |
| AC10 | verified | `assets/check-steering-anchors.sh:30`, case 29b, with both no-false-block halves |

An `init` run against a scratch project would move AC1, AC2 and AC6 from pinned to observed. #126 is the issue that does that work; it is not this spec's job, and claiming those three as verified here would be the kind of claim `docs/verified.md` exists to stop.

## Findings addressed in round 1

- **MEDIUM-1** — `skills/init/SKILL.md` told the operator that omitting the target makes the messages "fall back to naming both sets". The code names the three documents every project owes and offers both *set names* to declare. The sentence restated the ambush as advice, one paragraph after describing it correctly. Fixed.
- **MEDIUM-3** — AC7 is a conjunction, and only the question was pinned. The fenced-block line could be deleted with every guard green, leaving `init` to infer where the answer goes; a `- Target:` written into the wrong file resolves to nothing and the checker falls back having never seen it. A second `CONTRACTS` entry now pins the destination, with a case that mutates it. The reviewer noted the `- Mode:` entry carries the identical gap and did not escalate for that reason — that gap is untouched here and is worth its own issue.
- **MEDIUM-4** — this file.
- **LOW-2** — `DOC_OWNER`'s docstring said "three documents" while the dict now holds six and the message can name six. Fixed.
- **LOW-4** — the ask was unconditional while AC1 scopes it to a project with no `- Mode:` line. The only thing preventing a re-ask was a Rules line two sections away. Now stated where the ask is, and it admits the `bootstrap` re-run case, which is the one upgrade where a target is still useful.

## Findings recorded rather than fixed

- **MEDIUM-2 (version size)** — the reviewer argues `0.10.0` on #110's precedent, recorded at `.work_logs/2026-09-13.md:121`: a value on a machine-read line that `init` writes was sized minor. C4 in the spec anticipated the re-check. This is the operator's call and is not the reviewer's to settle; raised rather than applied.
- **LOW-1** — `Target` is a likelier prose noun in a tech document than the other six anchors, so `Target: Python 3.11` in a project's `.steering/tech.md` would false-block with the guard pointing at prose. Real, and `Mode` carries the same exposure with no case either. Accepted as parity rather than widened here: fixing it for one key and not the other would leave the guard inconsistent in a way the next reader has to rediscover.
- **LOW-3** — AC3 says "by path" and the message names bare filenames. The bootstrap branch deliberately never resolves the `docs` directory, so there is no path to name without reaching for one the mode does not require. The wording is inherited from the pre-existing message. Recorded; AC3's intent is "named, with its owning skill", which the message does.
- **LOW-5** — cases 71–73 sit physically above case 70. G-9 already records that this suite's source order and output order diverge; this is a further instance and is left rather than renumbered.
- **INFO** — `docs/DESIGN.md`, `CONTRIBUTING.md` and `scripts/test-gates.sh:485` all say "five machine-read lines"; there are now seven. Already stale at #110 and widened by this diff. Outside this spec's files and unguarded by `check-readme-claims.py`, so left for its own issue rather than corrected in passing.
