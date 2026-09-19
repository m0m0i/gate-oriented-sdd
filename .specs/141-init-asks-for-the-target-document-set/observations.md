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

## Review round 2 — CLEAN, 0 blockers, 0 HIGH, 2 MEDIUM, 1 LOW

Reviewed at `4ff120a68188f59e21038b7c9cbe6c6652229f17`. All five round-1 fixes confirmed real, C1 re-verified in the code. Two defects the round-1 fixes introduced or widened, both addressed:

- **MEDIUM-1** — `scripts/check-skill-contracts.py`'s docstring capped the list at "Eighteen today" while `CONTRACTS` had reached twenty; this branch added the nineteenth and twentieth without moving the number either time, so the file's own growth cap read as already exceeded. The suite's running count stopped in the same place. Both moved, and the count is now named in case 74's header where the next author will see it. This is LOW-2's defect one file over, which is the argument for fixing it rather than recording it.
- **MEDIUM-2** — the scoping clause added for round 1's LOW-4 admitted a case AC6 does not. A project at `- Mode: bootstrap` carries a `- Mode:` line, so on the literal reading it is an upgrade that must "change nothing else" — and the clause told `init` to ask and write `- Target:` in exactly that case, citing the Rules bullet it contradicted. The clause is now narrowed to AC1's own condition: ask only where no `- Mode:` line exists.
  The widening was tempting and is not free to keep: a `bootstrap` re-run is the one upgrade where a target is still useful, and a project that re-runs `init` before writing any document gets no chance to record its choice. Taking it would mean amending AC6 in its own commit, which is a scope change this spec did not agree. Left as the narrower behaviour, and worth its own issue.
- **LOW** — case 74's destination half asserted `*Target*`, a cue both Target pins print. Now asserts the needle, matching the precedent one case above.

## Review round 3 — CLEAN, 0 blockers, 0 HIGH, 1 MEDIUM, 1 LOW

Reviewed at `c0cbac707a420ea8c8daeddfdafa93bad1d22590`. All three round-2 fixes confirmed, no stale count left anywhere in the repo, C1 re-verified. Both new findings were defects the previous round's fixes introduced, and both are fixed:

- **MEDIUM** — the narrowed clause was evaluated *after* the same step writes `- Mode: bootstrap`, so "where no `- Mode:` line exists" was false in every case, including the fresh install AC1 is about. Round 1's wider wording had masked the collision; narrowing it removed the mask. The condition now names the state the project arrived in. This is the finding no pin could have caught — both pins check that the sentence is present, not that it ever fires — which is exactly the exposure the pinned-not-observed table above names, demonstrated rather than argued.
- **LOW** — the sentence added to the docstring said "#141 added two and moved this number twice". It moved once, in review, after both entries had landed. The exhibit asserted the opposite of the lesson it exists to teach, and contradicted this file one directory over. Corrected.

## Review round 4 — CLEAN, 0 blockers, 0 HIGH, 0 MEDIUM, 1 LOW

Reviewed at `36171138d61f4a09b4cfb9ca8e54e7eedb01abf6`. Both round-3 fixes confirmed against the branch's actual history, C1 re-verified, no new MEDIUM. The one LOW was advisory: the clause's stated *reason* said "this step has just written one in every case", which is false on an upgrade where the operator declines to move the mode up — this step then writes no `- Mode:` line at all. The conclusion held either way, but the reason is prose a model executes and was one reading from an instruction to write the line on an upgrade. Fixed rather than recorded, because leaving a known-false sentence in a skill body is the defect round 1's MEDIUM-1 was.

## Findings recorded rather than fixed

- **MEDIUM-2 (version size)** — the reviewer argues `0.10.0` on #110's precedent, recorded at `.work_logs/2026-09-13.md:121`: a value on a machine-read line that `init` writes was sized minor. C4 in the spec anticipated the re-check. This is the operator's call and is not the reviewer's to settle; raised rather than applied.
- **LOW-1** — `Target` is a likelier prose noun in a tech document than the other six anchors, so `Target: Python 3.11` in a project's `.steering/tech.md` would false-block with the guard pointing at prose. Real, and `Mode` carries the same exposure with no case either. Accepted as parity rather than widened here: fixing it for one key and not the other would leave the guard inconsistent in a way the next reader has to rediscover.
- **LOW-3** — AC3 says "by path" and the message names bare filenames. The bootstrap branch deliberately never resolves the `docs` directory, so there is no path to name without reaching for one the mode does not require. The wording is inherited from the pre-existing message. Recorded; AC3's intent is "named, with its owning skill", which the message does.
- **LOW-5** — cases 71–73 sit physically above case 70. G-9 already records that this suite's source order and output order diverge; this is a further instance and is left rather than renumbered.
- **INFO** — `docs/DESIGN.md`, `CONTRIBUTING.md` and `scripts/test-gates.sh:485` all say "five machine-read lines"; there are now seven. Already stale at #110 and widened by this diff. Outside this spec's files and unguarded by `check-readme-claims.py`, so left for its own issue rather than corrected in passing.
