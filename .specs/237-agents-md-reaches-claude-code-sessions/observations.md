# Observations: 237-agents-md-reaches-claude-code-sessions

What was run, against what, and what it printed. Each section names the commit it was observed at.

## The AC1 probe

A headless Claude Code session in this repository's root, with every tool disabled and every hook disabled. With tools disabled, the session can answer only from what was loaded into its context at start. With hooks disabled, the SessionStart steering digest cannot supply an answer either. Neither question is answered by `CLAUDE.md` alone, by `~/.claude/CLAUDE.md`, or by the steering digest. `AGENTS.md:58` and `AGENTS.md:64` answer them.

```
claude -p --tools "" --model sonnet --settings <settings.json> "$(cat probe.txt)" < /dev/null
```

`<settings.json>` disables every hook and pins **Project instructions**, the built-in `agents-md` plugin's option. Claude Code reads that option from a `--settings` file, so the user's own value cannot leak into the result. Two values are probed, the default and `claude-md`:

```
{"disableAllHooks":true,"pluginConfigs":{"agents-md@builtin":{"options":{"instructionFiles":"claude-md-or-agents-md"}}}}
{"disableAllHooks":true,"pluginConfigs":{"agents-md@builtin":{"options":{"instructionFiles":"claude-md"}}}}
```

A third value, `claude-md-and-agents-md`, loads `AGENTS.md` beside any `CLAUDE.md`, prose pointer or not. It is probed once in T1, to show the pin takes effect, and is not part of AC1.

`probe.txt`:

```
Answer only from the project instructions already loaded in your context. Do not guess, and do not infer from file names you have seen mentioned. Answer each question on its own line, prefixed Q1: and Q2:. If no loaded instruction answers a question, write exactly NOT-IN-CONTEXT for it.
Q1: What do your loaded project instructions say to do when the leakage guard fires on a file?
Q2: Why do your loaded project instructions say agents/_template/reviewer.md quotes its frontmatter placeholders?
```

## T1 — baseline, at `76669c1` (the spec commit; `CLAUDE.md` and `AGENTS.md` as on `main` at `04e026c`)

Claude Code 2.1.288, run 2026-10-04.

### AC1 probe, before

| `instructionFiles` | Q1 | Q2 |
| :-- | :-- | :-- |
| `claude-md-or-agents-md` (default) | `NOT-IN-CONTEXT` | `NOT-IN-CONTEXT` |
| `claude-md` | `NOT-IN-CONTEXT` | `NOT-IN-CONTEXT` |
| `claude-md-and-agents-md` (the pin check, not part of AC1) | answered from `AGENTS.md:58` | answered from `AGENTS.md:64` |

The third row answered, word for word:

```
Q1: Rewrite the file. Do not scrub it in place, because scrubbing leaves the shape, and the shape is where the private structure lives.
Q2: Bare `{{...}}` is a flow mapping in YAML. An unquoted placeholder would parse as an object and fail validation before substitution ever happens.
```

So the pin takes effect, and the two `NOT-IN-CONTEXT` rows are about the instruction files rather than the probe. Under the default and under `claude-md`, a session in this repository starts without `AGENTS.md`.

### AC2 comparison, before

A throwaway script compares the commands on `.steering/tech.md`'s `- Validators:` line with the `./`-prefixed commands in `AGENTS.md`'s `bash` block. It is not committed.

```
validators on the line: 13
block commands: 11
missing from the block: ./assets/check-document-set.py ./scripts/check-contract-path.py ./scripts/check-readme-claims.py ./scripts/check-reviewer-allow-list.py
order: DIFFERS (or commands missing)
block commands not on the line (PR-only guards expected): ./scripts/check-version-bump.py ./scripts/check-backlog-tracker.py
```

### AC3 grep, before

`grep -n "was #16, which is closed" AGENTS.md .claude/agents/gate-sdd-reviewer.md` finds two lines: `AGENTS.md:74` and `.claude/agents/gate-sdd-reviewer.md:50`.

### Validators, before

Every command on the `- Validators:` line exits 0:

| Validator | Exit | Last line |
| :-- | :-- | :-- |
| `check-leakage.sh` | 0 | clean — 300 file(s) scanned |
| `check-manifests.py` | 0 | both manifests agree |
| `check-markdown-fences.py` | 0 | 10 fence(s), no hand-wrapped prose |
| `check-receipt-schema.py` | 0 | 7 field(s) agree across 3 copies |
| `check-skill-contracts.py` | 0 | 25 skill contract(s) present |
| `check-templates.py` | 0 | 9 live spec(s), no task sequenced after the review |
| `check-steering-anchors.sh` | 0 | 6 of 7 anchor(s) resolved, none unreadable |
| `check-locks.py` | 0 | 6 pinned file(s) match their locks |
| `check-document-set.py` | 0 | mode `full` at `docs/` |
| `check-contract-path.py` | 0 | 12 source(s) agree on `_shared/reviewer-contract.md` |
| `check-readme-claims.py` | 0 | plugin.json is at v0.21.6 |
| `check-reviewer-allow-list.py` | 0 | 13 validator(s) covered |
| `test-gates.sh` | 0 | 175 passed, 0 failed, 0 skipped |

## T2 — after the three-file change, at the T2 commit (parent `8a05ed0`)

Claude Code 2.1.288, run 2026-10-04.

### AC1 probe, after

| `instructionFiles` | Q1 | Q2 |
| :-- | :-- | :-- |
| `claude-md-or-agents-md` (default) | answered from `AGENTS.md:58` | answered from `AGENTS.md:64` |
| `claude-md` | answered from `AGENTS.md:58` | answered from `AGENTS.md:64` |

Word for word, under the default:

```
Q1: Rewrite the file. Do not scrub it in place, because scrubbing leaves the shape, and the shape is where the private structure lives.
Q2: Bare `{{...}}` is a flow mapping in YAML. An unquoted placeholder would parse as an object and fail validation before substitution ever happens.
```

And under `claude-md`:

```
Q1: If the guard fires, rewrite the file — do not scrub it in place. Scrubbing leaves the shape, and the shape is where the private structure lives.
Q2: Bare `{{...}}` is a flow mapping in YAML, so an unquoted placeholder parses as an object and fails validation before substitution ever happens.
```

Both rows went from `NOT-IN-CONTEXT` to `AGENTS.md`'s text. The only change between the two runs that a session loads at start is the `@AGENTS.md` line. **AC1 holds.**

### AC2 comparison, after

```
validators on the line: 13
block commands: 15
missing from the block: none
order: the block lists the line's commands in the line's order
block commands not on the line (PR-only guards expected): ./scripts/check-version-bump.py ./scripts/check-backlog-tracker.py
```

The four comments come from each script's own docstring. **AC2 holds.**

### AC3, after

The grep finds no file stating the #16 reason. For each file, a script took the line from `HEAD` (`8a05ed0`), removed the one sentence, and found the result among the file's new lines: `AGENTS.md:74` True, `.claude/agents/gate-sdd-reviewer.md:50` True. Each paragraph is the old one minus that sentence, and its #19 reason and ADR-6 pointer stand. **AC3 holds.**

`git diff --word-diff` attributes the `AGENTS.md` removal as "older reason … directories. The", taking the paragraph's second "The" rather than its first. That is the diff's alignment, not a change in wording.

### Validators, after

All 13 exit 0, with the same last lines as in T1. `test-gates.sh` reports 175 passed, 0 failed, 0 skipped. `check-contract-path.py` still reports 12 sources agreeing on `_shared/reviewer-contract.md`, so `AGENTS.md:63`, which was left alone, still names the contract.

<!-- T3 section follows -->
