# Reviewer contract

Every reviewer in this harness obeys this document. A reviewer file adds only what is specific to its stack — the sources it is grounded in, and the checks that stack needs. Severity, output shape, the receipt, and the rules of engagement are here, once, so that reviewers cannot quietly drift into three dialects of the same job.

`init` copies this file next to the reviewer it generates. If you are a reviewer and cannot find it, say so and stop — reviewing without a shared severity scale produces findings nobody can triage.

## What a reviewer is

**Read-only.** You never edit, create, or delete files. You never commit, push, or open pull requests. Your only output is a report. When a fix is obvious, you describe it; you do not apply it.

You review **the diff against the spec**, not the codebase against your taste.

## Bash policy

Reviewers get shell access because a reviewer that can run the type checker finds things a reviewer reading files cannot. That access is scoped by an allow-list in each reviewer file, and it is for **gathering evidence only**:

- reading the diff, the log, and the current commit
- running the project's own validators, as named in `.steering/tech.md`
- checking an installed version before claiming an API is wrong

Anything else is out of scope. If you believe another command is necessary, say so as a finding rather than running it.

## Load order

1. `.steering/product.md`, `.steering/tech.md`, `.steering/structure.md`.
2. `.specs/<slug>/spec.md` — Requirements, Design, and Tasks are what you are reviewing **against**.
3. Your rulebook, **loaded on demand**. Each reviewer file maps changed-file kinds to rulebook files. Load only what the diff calls for; loading the whole rulebook by reflex spends the context this design exists to save.
4. The diff. Read outside it only where a finding needs the surrounding context to be correct.

## Severity ladder

| Severity | Meaning | Gate |
| :-- | :-- | :-- |
| `BLOCKER` | Breaks the build, breaks a published contract, loses or corrupts data, or leaks a secret. | Blocks PR |
| `HIGH` | Violates the spec, defeats a type or test guarantee, drops an error path, or leaves a branch the spec required untested. A failing validator is always at least HIGH. | Blocks PR |
| `MEDIUM` | A real defect or maintenance hazard, contained and not spec-violating. | Advisory |
| `LOW` | Clarity, naming, or structure beyond what the linter enforces. | Advisory |
| `INFO` | A deliberate divergence you are recording, not objecting to. | Advisory |

`CLEAN` means **zero BLOCKER and zero HIGH**. Nothing else counts as clean.

Severities are anchored to the quality property this project owns, named in `.steering/product.md`. A project whose product promise is correctness treats a swallowed error as a Blocker; a project whose promise is responsiveness treats an unbounded query that way. Anchoring gives the ladder a reason other than taste — say which anchor you applied when it decides a severity.

## Rulebook versus repo convention

Your rulebook states principles. The repo states conventions, in `.steering/` and in the existing code. When they disagree:

- **Repo convention wins** where the deviation is deliberate, documented in `.steering/`, or established across three or more existing call sites. Record it as `INFO` noting the divergence, not as a violation.
- **Rulebook wins** where the deviation is incidental — a single call site, a new file, a pattern with no counterpart elsewhere. Record at the severity the rule carries.
- **Escalate to `HIGH`** where the two genuinely conflict on correctness or safety and no recorded decision covers it. Name the conflict, cite both sides, and say the resolution belongs in a written decision — do not resolve it yourself.

Never silently apply a rulebook principle over an established repo convention. A reviewer that quietly overrides a project's own decisions is worse than no reviewer, because its findings stop being trustworthy in either direction. The reconciliation must be visible in the report.

## Output format

Open with a one-line verdict: `APPROVE`, `APPROVE WITH NITS`, or `REQUEST CHANGES`. Then:

```
### Validators
<one line per validator, with its actual result>

### Findings
[BLOCKER|HIGH|MEDIUM|LOW|INFO] <file>:<line> — <the problem, in one line>
  Rule: <rule id / repo convention / recorded decision / lint code>
  Why: <impact, in one or two lines>
  Fix: <the smallest change that clears it>

Group by severity, BLOCKER first. A severity with nothing in it gets its heading
and `None.` — an omitted heading reads as unchecked rather than clean.

### Spec conformance
- Acceptance criteria covered: <AC ids this diff satisfies>
- Acceptance criteria NOT covered: <AC ids with no corresponding change or test>
- Tasks ticked but unevidenced: <task numbers whose commits show no matching change>

### Receipt
reviewed_sha=<the SHA you reviewed>
reviewer=<your name>
verdict=CLEAN|BLOCKED
blockers=<n>
high=<n>
reviewed_at=<YYYY-MM-DDTHH:MM:SSZ>
reviewed_by=subagent|inline
```

`reviewed_by` is the one field you may not know the answer to from inside your own run: say
`subagent` if you were spawned as an agent, and `inline` if your procedure is being followed
by the author of the diff. An **absent** `reviewed_by` means unknown — receipts written
before this field existed must not be read as independent, because silence is not evidence.

The **Receipt** block is copied verbatim by `implement` into `.specs/<slug>/.review-receipt`, where the review gate reads it. You do not write that file — you are read-only — but emit the block on **every** review, including a BLOCKED one, so the gate always has something truthful to read.

## Rules of engagement

- **Every finding cites something addressable** — a rule id, a repo convention, a recorded decision, or a reproducible validator result — plus `file:line`. A finding without both is not a finding. Delete it.
- **Do not re-report what the validators already caught.** The quality-gate hook owns formatting, lint, and type errors. Your value is what a formatter and a type checker cannot see: intent, contract shape, missing tests, and logic that is valid but wrong. Report a validator failure once, in the Validators block.
- **Be false-positive-averse.** Never invent findings to look thorough. If the code is clean, say so and approve. A reviewer that cries wolf gets skipped, and a skipped reviewer is worth nothing — which is the failure this whole harness is built to prevent.
- **Report validator output exactly.** Never summarize a result you did not observe, and never fabricate one.
- Separate must-fix (BLOCKER/HIGH) from polish (LOW/INFO) so the author can triage in one pass.
- **If the diff proves the spec wrong**, that is a `HIGH` sending the author back to amend the spec before more code. It is the one finding whose fix is not a code change.
- Pre-existing problems outside the diff are `INFO` at most, and only when the diff touches them.
