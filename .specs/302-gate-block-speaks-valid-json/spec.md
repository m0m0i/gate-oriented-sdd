# Spec: A gate's block is valid JSON whatever its message holds, and the hook file says which harness reads it

- Slug: 302-gate-block-speaks-valid-json   Issue: 302   Type: bug   Status: approved
- Author: m0m0i (Claude Code)   Date: 2026-10-26

Backlog row 1's next spec ("Antigravity ready"), after #324 and #330 shipped as #345. #302 is two defects in the nine lines of `gate_block` (`hooks/gate-lib.sh:31-46`), one on each harness. Both turn a block into a pass with no message.

## 1. Requirements (WHAT / WHY)

### Part 1: on Antigravity, bytes the escape does not handle make the block unparseable

- **Reproduction:**
  1. A validator on the `- Validators:` line fails and prints ANSI colour, for example `printf '\033[31mFAIL\033[0m\n'; exit 1`.
  2. The quality gate runs on Antigravity, where `_gate_block_status` returns 0 (`hooks/gate-lib.sh:41-46`).
  3. `gate_block` prints `{"decision":"continue","reason":"…"}` holding a raw ESC byte, and exits 0.
- **Expected:** the block's stdout is one JSON object that Antigravity's parser accepts, whatever bytes the message holds. RFC 8259 §7 forbids raw control characters in a string. Antigravity parses hook stdout with Go's protojson, which rejects a raw byte below 0x20 and any invalid UTF-8 inside a string (`internal/encoding/json/decode_string.go`, `parseString`). It accepts `\u00XX` escapes and valid multibyte UTF-8.
- **Actual:** `_gate_json_escape` (`hooks/gate-lib.sh:19-28`) escapes only `\`, `"`, CR and tab, and joins lines with `\n`. Measured in a scratch directory on this branch's base (`969dbb1`):
  - **Control bytes.** ESC, BEL, BS, VT, FF and the rest of 0x01 to 0x1F pass through raw, and `json.loads` rejects the object. A14 (`docs/verified.md:507`) saw Antigravity drop such a block and end the turn with `status: SUCCESS` for a raw tab, before #282 escaped tabs.
  - **Invalid UTF-8, under a UTF-8 locale.** BWK awk aborts at the first bad byte (`towc: multibyte conversion failure`). Every line from there on is lost, and the reason can be empty. `gate_block` ignores the escape's exit status, because it sits inside `printf`'s arguments.
  - **Invalid UTF-8, under `LC_ALL=C`.** The bytes pass raw, which protojson rejects.
  - **`gate_replay` re-emits the child's verdict as it is** (`hooks/gate-lib.sh:733-749`). It checks the shape only, so an invalid verdict from the bounded child reaches the harness unchanged.
- **Impact:** every Antigravity project whose validator prints colour or other control bytes, or output that is not UTF-8, on every turn that should block. That is a gate exiting 0 when it should block, at least HIGH under `- Owns: gates never fail open`. The colour case needs no damage: `pytest --color=yes` and most linters under a TTY-forcing flag do it.
- **Root cause:** `_gate_json_escape` was written for messages the gates compose. Its comment says "Gate messages are ours, not user input" (`hooks/gate-lib.sh:17-18`), and every message since has carried validator output (`quality-gate.sh:590-592`, `:323`, `:359`), file and branch names, and receipt values. #282 added the CR and tab escapes A14 named, by listing bytes. So the escape is a list of bytes known to be bad, not a rule for what JSON accepts. It also runs in whatever locale the hook inherits, which decides whether invalid UTF-8 aborts it or passes through it. No test feeds it a control byte other than tab: the probe the #282 section titles "carriage returns" holds no CR byte (`scripts/test-gates.sh:3193-3195`, `od -c`).

### Part 2: on Claude Code, an inherited Antigravity variable turns every block into a pass

- **Reproduction:** start `claude` from a shell that inherited `ANTIGRAVITY_CONVERSATION_ID` or `ANTIGRAVITY_AGENT`, for example a terminal inside an Antigravity agent's session. End a turn that should block.
- **Expected:** the gate blocks the way Claude Code reads a block: exit 2, with the message on stderr.
- **Actual:** `_gate_block_status` sees the inherited variable, so `gate_block` exits 0 with `{"decision":"continue",…}`, and Claude Code ends the turn. The bootstrap guards at `hooks/quality-gate.sh:51-58` and `hooks/review-gate.sh:53-60` copy the same test. Measured on this branch's base, from this session's Bash tool: `ANTIGRAVITY_CONVERSATION_ID=x` with no Antigravity present gives exit 0. The mirror case exists too. Claude Code exports `CLAUDECODE=1` and `CLAUDE_CODE_SESSION_ID` to every shell it starts, so any rule keyed on those would break an Antigravity session started from a Claude Code terminal the same way.
- **Impact:** every gate on Claude Code, in a session whose environment carries an Antigravity variable. It is unmeasured how often that happens. The harnesses' environments are not documented to be isolated from each other.
- **Root cause:** the gate decides which harness is reading it from ambient environment variables. A nested session inherits those, while the hook file that invokes the gate knows its harness for certain and says nothing: `.claude-plugin/hooks.json` names only the gate, and `hooks/templates/antigravity.hooks.json` runs `sh {{HOOKS_DIR}}/<gate>.sh` with no marker.

### Acceptance criteria

- [ ] **AC1:** WHEN a gate blocks with a message holding any byte from 0x01 to 0x1F, or DEL THE SYSTEM SHALL print a JSON object that a strict parser accepts. The control bytes are escaped (`\n`, `\r`, `\t` short, the rest `\u00XX`), DEL stays as it is, and the message text is otherwise kept.
- [ ] **AC2:** WHEN the message holds invalid UTF-8 THE SYSTEM SHALL print valid UTF-8, with each invalid byte replaced by U+FFFD, written as the escape `\ufffd` (C3), and every valid character kept. This covers a stray continuation byte, 0xC0, 0xC1, 0xF5 to 0xFF, an overlong form, an encoded surrogate, and a multibyte character cut short. It SHALL do the same whatever locale the hook inherits.
- [ ] **AC3:** WHEN the escape itself fails THE SYSTEM SHALL still block, with a fixed reason that says the message could not be encoded and is on stderr. It never blocks with an empty or cut-short reason, and never passes.
- [ ] **AC4:** WHEN the bounded child's verdict reaches `gate_replay` holding a raw control byte or invalid UTF-8 THE SYSTEM SHALL treat it as no verdict, as it does a malformed one today. The parent then blocks on its own, so an unparseable verdict is never replayed.
- [ ] **AC5:** WHEN a hook file runs a gate THE SYSTEM SHALL know the harness from that hook file: the Antigravity template and the plugin's Claude Code entry each say which harness they are, as `GATE_SDD_HARNESS` (C1). The Antigravity template runs each gate as `GATE_SDD_HARNESS=antigravity sh …`, and `hooks/plugin-gate.sh` exports `GATE_SDD_HARNESS=claude-code` before it runs a gate, so every Claude Code project gets the marker by plugin update. With the marker, an inherited variable of the other harness changes nothing: exit 2 on Claude Code, and exit 0 with the JSON on Antigravity. `scripts/check-manifests.py` fails an Antigravity template whose `Stop` entries lack it.
- [ ] **AC6:** WHEN a gate runs from a hook file with no marker, as an Antigravity project not yet re-`init`ed does, THE SYSTEM SHALL keep today's reading, so that no installed project changes behaviour until its hook file does. The bootstrap guards decide the same way as `gate_block`.
- [ ] **AC7:** WHEN this ships, these say what the code does: `docs/fidelity.md` (the blocking rows and its `gate_block` description), `docs/verified.md`'s A14, the comment at `hooks/gate-lib.sh:17-18`, `skills/init/SKILL.md`'s Antigravity bullet, `hooks/templates/README.md`, and the #282 test section's title.
- [ ] **AC8:** each regression case fails on `main` for the stated reason and passes after the fix.
- [ ] **AC9:** WHEN this ships THE SYSTEM SHALL have a recorded run on Antigravity CLI 1.4.7 in `docs/verified.md` (C2). It records whether:
  - a `Stop` block whose reason holds a raw ESC is dropped, as A14 saw for a tab on 1.3.3;
  - a block whose reason holds `\u001b`, `\ufffd` and raw valid UTF-8 is honoured;
  - a gate run as `GATE_SDD_HARNESS=antigravity sh …` sees the marker and blocks;
  - the real quality gate, from the rendered template, blocks on a validator that prints colour.

### Out of scope

- **Moving Claude Code to JSON on exit 0.** Claude Code blocks on `{"decision":"block"}` at exit 0, but a malformed object there is a pass, where exit 2 blocks whatever stdout holds. This spec does not give up that robustness.
- **#198 and #199:** `gate_block`'s shape surviving truncation, and its pin. This spec changes what it prints, not whether it survives a cut.
- **The steering digest** (`steering-digest-antigravity.sh`), which uses Python's `json.dumps` and is no gate.
- **NUL bytes.** `sh` drops them in command substitution before any escape sees them.

### Clarifications

Asked and answered on 2026-10-26.

- **C1: how a gate knows which harness reads its block.** Answer: **a marker in each hook file**, `GATE_SDD_HARNESS`.
  - The Antigravity template sets it on each gate's command, and `plugin-gate.sh` exports it for Claude Code. This repository's own `.claude/settings.json` sets it too.
  - The marker wins over ambient variables. With no marker, the gate keeps today's reading (AC6).
  - Not taken: reading the hook's stdin, which the gates pass through to the validators and whose Antigravity `Stop` shape was never recorded. Also not taken: one exit-0 `{"decision":"block"}` output for both harnesses, which would make a malformed object a pass on Claude Code. AC5 amended.
- **C2: probing the local Antigravity CLI 1.4.7 during implement.** Answer: **yes**, as for #324, in a `mktemp -d` project under the trusted folder, recorded in `docs/verified.md`. AC9 added.
- **C3: what replaces an invalid UTF-8 byte.** Answer: **U+FFFD, written as `\ufffd`.** The escape's output stays ASCII plus the valid UTF-8 it kept, protojson accepts the escape, and a reader sees where bytes were lost. Not taken: `?`, which a reader cannot tell from a real one, and dropping the bytes, which hides the loss. AC2 amended.
- **C4, decided here, not asked: an unknown `GATE_SDD_HARNESS` value falls back to today's reading**, as no marker does. No value is guessed, and a typo in a hand-edited file behaves as an old file does.
- **C5, decided here, not asked: the decision word stays `"continue"`.** A2 saw Antigravity honour `"continue"` and `"block"` alike on 1.3.3, and the probe re-tests `"continue"` on 1.4.7. A change of word is a change no finding asks for.

## 2. Design (HOW)

### Fix approach

**Part 1: an escape that encodes, not one that lists bad bytes.** `_gate_json_escape` runs its awk under `LC_ALL=C`, so the input is bytes in every locale and the tool never aborts on them. The 2026-10-17 `tr` fix (`gate_hook_timeout`) was the same lesson. In `BEGIN` it builds a byte-to-value table from `sprintf("%c", i)` for 1 to 255, then walks each record a byte at a time:
- `\` and `"` are backslash-escaped. Tab and CR use their short forms, every other byte below 0x20 becomes `\u00XX`, and records are joined with `\n` as today.
- Bytes 0x20 to 0x7F, DEL included, are copied.
- A byte of 0x80 or above starts a UTF-8 sequence. It is copied whole only when it is well formed, using RFC 3629's table:
  - `C2..DF` needs one continuation byte;
  - `E0` needs a second byte of `A0..BF`, `ED` one of `80..9F`, and the rest of `E1..EF` one of `80..BF`, then one more continuation byte;
  - `F0` needs a second byte of `90..BF`, `F4` one of `80..8F`, and `F1..F3` one of `80..BF`, then two more continuation bytes.
- Any other byte, and the lead of a sequence that fails these checks, becomes `\ufffd`, and the walk moves on one byte. So each invalid byte is one replacement, and a valid character after it is kept (AC2).

The output is ASCII plus the valid UTF-8 it kept. No `\u` surrogate is ever written, so protojson's surrogate rule cannot fire.

**AC3, fail closed.** `gate_block` captures the escape into a variable before its `printf`. It uses that value only when the awk pipeline exited 0 and printed something for a non-empty message. Otherwise the reason is a fixed ASCII sentence: the message could not be encoded, and it is on the gate's stderr. stderr always carries the raw message, as today.

**AC4, the replay.** `gate_replay` keeps its one-line, `cmp` and shape checks, and adds one more through the same awk in a check mode (`mode=check`). The verdict line must hold no byte below 0x20 and no invalid UTF-8. A line that fails is no verdict, which the parent already turns into a block of its own (`hooks/gate-lib.sh:739-749`).

**Part 2: the hook file names the harness.** `_gate_block_status` reads `GATE_SDD_HARNESS` first:
- `antigravity` returns 0;
- `claude-code` returns 2;
- anything else, unset included, falls to today's `ANTIGRAVITY_*` test (AC6, C4).

The two bootstrap guards (`quality-gate.sh:51-58`, `review-gate.sh:53-60`) get the same `case` before their own copy of that test, because they run when `gate-lib.sh` cannot be read. Case 159, which holds them equal to `gate_block`, gains the marker.

The marker is set in each place a hook file runs a gate:
- `hooks/templates/antigravity.hooks.json`: each `Stop` command ends `GATE_SDD_HARNESS=antigravity sh {{HOOKS_DIR}}/<gate>.sh`.
- `hooks/plugin-gate.sh`: `export GATE_SDD_HARNESS=claude-code` before its `exec sh "$DIR/$gate"`. That reaches every Claude Code project by plugin update, with no change to `.claude-plugin/hooks.json`.
- This repository's own `.claude/settings.json`, which runs the gates from source: `GATE_SDD_HARNESS=claude-code sh hooks/<gate>.sh`.

`scripts/check-manifests.py` fails an Antigravity template whose `Stop` command for either gate lacks `GATE_SDD_HARNESS=antigravity sh ` before the gate's path.

The marker reaches the validators too, since they inherit the gate's environment. `scripts/test-gates.sh` already unsets `ANTIGRAVITY_*` at its top (`:26`), and it unsets `GATE_SDD_HARNESS` there as well. Otherwise the suite, run as this repository's own validator under the Claude Code marker, would read its Antigravity cases as Claude Code.

**The probe (AC9, C2) is split.** T1 runs first, before any code, with stand-in hooks that print hand-made verdicts: a raw ESC, the escaped forms, and the marker. T6 runs after the code: the real quality gate, from the rendered template, against a validator that prints colour. If T1 finds an escaped reason not honoured, implementation stops there.

### Affected files

- `hooks/gate-lib.sh`: `_gate_json_escape`, `gate_block`, `_gate_block_status`, `gate_replay`, and the comment at `:17-18`
- `hooks/quality-gate.sh`, `hooks/review-gate.sh`: the bootstrap guards
- `hooks/plugin-gate.sh`: the export
- `hooks/templates/antigravity.hooks.json`, `.claude/settings.json`
- `scripts/check-manifests.py`
- `scripts/test-gates.sh`: cases 392 onward, the #282 probe given a real CR, case 159, and the `unset` at `:26`
- `docs/fidelity.md`, `docs/verified.md`, `skills/init/SKILL.md`, `hooks/templates/README.md`
- `plugin.json`, `.claude-plugin/plugin.json`: 0.38.0, after the receipt. It is minor: the gates' output and the rendered template change.

### Blast radius

- **Every block passes through the new escape.** A message that today's escape already handled comes out byte for byte the same: ASCII, valid UTF-8, tab, CR and newline. Case 283, which compares a replayed block with a direct one byte for byte, shows no drift.
- **`gate_replay` gains a check.** A verdict from today's child that held a raw control byte was replayed and unparseable. Now the parent blocks on its own, with its own message. That is a block either way, and now a readable one.
- **Installed projects.**
  - A Claude Code project gets the marker with the plugin.
  - An Antigravity project keeps today's reading until `init` re-renders its file (#343). Meanwhile its gates still come from its copies, so the escape fix needs that re-run too. The upgrade note says so.
  - Neither project passes where it blocked before.
- **The marker is inherited by whatever a gate spawns.** A validator that started a nested harness session would hand it the parent's marker. Nothing here does that, and test-gates' `unset` covers the one suite that runs gates inside a gate.
- **The escape's cost** is a byte loop in awk over at most the 20-line tails the gates pass it. That is microseconds against the validator run.

### Why this cannot recur

- The escape stops being a list. It encodes by RFC 8259's and RFC 3629's rules, so a new bad byte has no list to be missing from.
- Case 392 feeds every byte from 0x01 to 0xFF, alone and in sequences, under both locales. A strict check decodes the bytes as UTF-8 with no replacement, then parses the JSON and refuses any surrogate. Python's `json.loads` alone would accept a lone surrogate escape.
- Case 159 holds the bootstrap guards to `gate_block`, and `check-manifests.py` holds the template's marker.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [x] T1: **Probe, with stand-ins (AC9's first three items).** On Antigravity CLI 1.4.7, in a trusted `mktemp -d` project, run `Stop` stand-ins that print:
  - a raw-ESC reason;
  - a reason with `\u001b`, `\ufffd` and raw valid UTF-8;
  - a block under `GATE_SDD_HARNESS=antigravity sh …`, which logs the marker it sees.

  Record each in `docs/verified.md`. Stop if an escaped reason is not honoured.
- [ ] T2: **The escape (AC1, AC2).**
  - Red: case 392 sweeps 0x01 to 0x1F and DEL through `gate_block`, under `LC_ALL=C` and a UTF-8 locale, on both channels, with the strict check above. It fails on `main` at ESC. Case 393 does the same with the invalid UTF-8 classes in AC2 between valid Japanese text. It expects each bad byte as one `\ufffd` and the Japanese kept, and fails on `main` with an empty or raw reason. The #282 probe gets a real CR byte.
  - Green: the new `_gate_json_escape`.
- [ ] T3: **Fail closed (AC3).**
  - Red: case 394 runs `gate_block` with an `awk` on `PATH` that exits 1. It expects a block on both channels with the fixed reason and parseable JSON. On `main` the reason is empty.
  - Green: `gate_block` checks the escape.
- [ ] T4: **The replay (AC4).**
  - Red: case 395 hands `gate_replay` a child verdict of the right shape whose reason holds a raw ESC. It expects no replay: the parent's own block.
  - Green: the check mode.
- [ ] T5: **The marker (AC5, AC6).**
  - Red, cases 396 to 400:
    - `GATE_SDD_HARNESS=claude-code` with an inherited `ANTIGRAVITY_*` exits 2, through `gate_block` and through both bootstrap guards;
    - `GATE_SDD_HARNESS=antigravity` with `CLAUDECODE=1` exits 0 with the JSON;
    - no marker with an `ANTIGRAVITY_*` variable exits 0, today's reading kept;
    - `plugin-gate.sh` run with an inherited Antigravity variable blocks with exit 2;
    - the rendered template's `Stop` command blocks with exit 0, and `check-manifests.py` fails a template whose marker was removed.

    Case 159 gains the marker, and the suite unsets `GATE_SDD_HARNESS` at its top.
  - Green: `_gate_block_status`, the bootstrap guards, `plugin-gate.sh`, the template, `.claude/settings.json`, and the check.
- [ ] T6: **Probe, end to end (AC9's last item).** The real gates from this branch, rendered from the template into a trusted `mktemp -d` project. A validator prints colour and fails, and the quality gate blocks on Antigravity CLI 1.4.7. Record it.
- [ ] T7: **Docs (AC7).** The documents AC7 lists, with A14 brought up to date. Every validator passes.

The 0.38.0 bump is not a task. It lands after the receipt (#113).
