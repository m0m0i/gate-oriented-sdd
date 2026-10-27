#!/bin/sh
# gate-lib.sh — shared plumbing for this harness's gates.
#
# The two target harnesses signal "do not end this turn" differently:
#
#   Claude Code   exit code 2, message on stderr
#   Antigravity   {"decision":"continue","reason":"..."} on stdout, exit 0
#
# Rather than maintain two scripts, a gate emits BOTH. Each harness reads the
# channel it understands and ignores the other, so one script is authoritative
# and the two can never drift apart.
#
# Usage:  . "$(dirname "$0")/gate-lib.sh"
#         gate_block "message the model needs to read"
#         gate_pass

# A JSON string's contents for any message (#302). A gate's message carries bytes it did not
# write: a validator's output tail, a file or branch name. Antigravity parses the block with Go's
# protojson, which rejects a raw byte below 0x20 or invalid UTF-8 in a string, and a rejected Stop
# result ends the turn as a pass. So this encodes by rule rather than listing bad bytes:
#
#   - `\` and `"` are escaped, tab and CR take their short forms, every other byte below 0x20
#     becomes \u00XX, and lines are joined with \n;
#   - 0x20 to 0x7F, DEL included, are copied;
#   - a byte of 0x80 or above is copied with its sequence only when that sequence is well formed
#     by RFC 3629's table. Any other byte becomes �, one per byte, and the walk moves on one.
#
# awk runs under LC_ALL=C, so its input is bytes whatever locale the hook inherits: a UTF-8 locale
# aborts BWK awk at the first invalid byte and the message is cut short, which is the 2026-10-17
# `tr` lesson again. No \u surrogate is ever written.
#
# With `check` as $2 it prints nothing, and returns 1 when the text holds a byte below 0x20 or
# invalid UTF-8: gate_replay's test for a verdict the harness could parse.
_gate_json_escape() {  # <message> [check]
  printf '%s' "$1" | LC_ALL=C awk -v check="${2:-}" '
    function e(s) { if (check == "") printf "%s", s }
    function cont(s, j, lo, hi,   v) { v = ord[substr(s, j, 1)] + 0; return v >= lo && v <= hi }
    function seq(s, i, b,   lo, hi) {
      if (b >= 194 && b <= 223) return cont(s, i + 1, 128, 191) ? 2 : 0
      if (b >= 224 && b <= 239) {
        lo = b == 224 ? 160 : 128; hi = b == 237 ? 159 : 191
        return (cont(s, i + 1, lo, hi) && cont(s, i + 2, 128, 191)) ? 3 : 0
      }
      if (b >= 240 && b <= 244) {
        lo = b == 240 ? 144 : 128; hi = b == 244 ? 143 : 191
        return (cont(s, i + 1, lo, hi) && cont(s, i + 2, 128, 191) && cont(s, i + 3, 128, 191)) ? 4 : 0
      }
      return 0
    }
    BEGIN { for (i = 1; i < 256; i++) ord[sprintf("%c", i)] = i }
    {
      if (NR > 1) e("\\n")
      n = length($0)
      for (i = 1; i <= n; i++) {
        c = substr($0, i, 1); b = ord[c] + 0
        if (c == "\\" || c == "\"") e("\\" c)
        else if (b < 32) { bad = 1; e(b == 9 ? "\\t" : b == 13 ? "\\r" : sprintf("\\u%04x", b)) }
        else if (b < 128) e(c)
        else if (k = seq($0, i, b)) { e(substr($0, i, k)); i += k - 1 }
        else { bad = 1; e("\\ufffd") }
      }
    }
    END { exit (check != "" && bad) ? 1 : 0 }'
}

# Block the turn. Speaks to both harnesses, exiting 0 for Antigravity and 2 for Claude Code.
gate_block() {
  _msg=$1
  printf '{"decision":"continue","reason":"%s"}\n' "$(_gate_json_escape "$_msg")"
  printf '%s\n' "$_msg" >&2
  _gate_block_exit
}

# The status each harness reads as a block once the JSON and the message are out: 0 on
# Antigravity, which reads the JSON, and 2 on Claude Code. gate_replay asks it too, so a replayed
# block is judged by the same test that ends one.
_gate_block_status() {
  if [ -n "${ANTIGRAVITY_CONVERSATION_ID:-}" ] || [ -n "${ANTIGRAVITY_AGENT:-}" ]; then
    return 0
  fi
  return 2
}

# The end of every block: gate_block's, and gate_replay's when it hands a child's block on. In a
# gate's child it first marks the verdict complete, as gate_pass does (gate_replay, below).
_gate_block_exit() {
  [ -z "${_gate_child_run:-}" ] || { printf '' > "$_gate_child_run/end"; } 2>/dev/null
  _gate_block_status
  exit "$?"
}

# Allow the turn to end. Antigravity expects a JSON object; Claude Code expects
# exit 0 and ignores stdout here.
gate_pass() {
  printf '{}\n'
  [ -z "${_gate_child_run:-}" ] || { printf '' > "$_gate_child_run/end"; } 2>/dev/null
  exit 0
}

# The run directory of the gate's child, set by the child alone once it has checked the directory
# it was handed (#304). gate_pass and _gate_block_exit write `end` there after their output and
# before they exit, which is what tells the parent the verdict is whole. Unset here, on load, so a
# value inherited from the environment can never mark a forged verdict complete.
unset _gate_child_run

# How long a gate may take, stated once (#304). Neither harness turns a Stop hook it timed out
# into a block: Claude Code discards a block written after its TERM, and Antigravity's KILL
# cannot be caught. So a gate has a verdict only if it reaches one by a deadline of its own,
# ahead of the hook's timeout. A ceiling is the `timeout` a hook file is meant to give its gate,
# and the gate also bounds itself by any shorter one it can see (gate_hook_timeout below). The
# margin is what a gate keeps back from a timeout to start its watchdog, finish the kill and
# write its block, counting the harness's own TERM-to-KILL grace as zero, because a block written
# after TERM is discarded. Plain assignments, never environment reads, so an inherited variable
# cannot move a deadline; and no other budget is written as a literal anywhere in hooks/.
_gate_margin=10
_gate_qg_ceiling=600
_gate_rg_ceiling=120
_gate_qg_default=170
_gate_qg_max=$((_gate_qg_ceiling - _gate_margin))
_gate_rg_budget=$((_gate_rg_ceiling - _gate_margin))

# Read one machine-read value out of a steering file.
#
# THE definition of how a steering anchor is read. Five call sites across the three hooks
# used to carry this expression by hand, and a sixth — the anchor check in assets/ — needs
# to ask the same question the gates ask. A copy that can disagree with its subject is the
# defect #14 and #23 are about; this exists so there is nothing to disagree with.
#
# Exact by design. `- **Owns: ...**` does not match, and that is correct: the consumer would
# not match it either, so a checker using this function sees precisely what a gate sees.
#
# Two forms, one expression. This one keeps "absent" and "unreadable" apart, the way
# _gate_read below does for whole files:
#
#   0  the file was there and readable when tested; stdout is the value, and empty when the
#      file does not carry the key
#   1  no such file
#   2  the file is there and could not be read
#
# "When tested" is doing real work in that first line: `[ -r ]` is a prediction, and the sed
# below still discards its own stderr, so an EIO or a mode change between the test and the
# open returns 0 with empty stdout — "read it, found nothing" for a read that failed. Narrower
# than the residue `_gate_read` leaves, and left there on purpose: closing it means changing
# the sed line, and every caller of gate_steering_value reads through it.
#
# An absent KEY stays fused with an empty value, deliberately: a steering file legitimately
# omits `- Docs:`, so no caller treats a missing key as an error. What was never legitimate is
# answering at all for a file nobody could open. The empty string said that too, and every
# caller read it the one way — nothing found, so nothing wrong. quality-gate.sh reached
# gate_pass on a mode-000 tech.md having run no validator, and check-steering-anchors.sh
# recovered the distinction with a hand-rolled `[ ! -r ]`, which is what proves it was
# recoverable and that here is where it should have been recovered. #39.
gate_steering_read() {  # <file> <key>
  [ -f "$1" ] || return 1
  [ -r "$1" ] || return 2
  sed -n "s/^ *- *$2: *//p" "$1" 2>/dev/null | head -1
}

# The value-only form, for the callers that do not need the difference — which is most of
# them, since an absent steering file and an unreadable one are equally "no value here" to a
# digest line or an optional glob. Always exits 0, and prints exactly what it printed before
# the reader above existed: empty for an absent file, an unreadable one, a directory, or a
# file without the key. A wrapper rather than a second copy of the sed, for the reason this
# function exists at all — and a caller that does not opt in is behaviourally unchanged,
# which is the point. #182 spent seven review rounds inside gate_work_reached_base; this is
# not the branch that reopens it.
gate_steering_value() {  # <file> <key>
  gate_steering_read "$1" "$2"
  return 0
}

# The quality gate's budget, from `- Validator budget: <seconds>` in a tech.md (#304, AC7).
#
#   0  the line holds an integer from 1 to _gate_qg_max; stdout is it
#   1  no such line, or no such file; stdout is _gate_qg_default. Not an error: most projects
#      write no line. A status of its own so a caller can say which of the two set the budget
#   2  the line is there and holds anything else, the empty value included; stdout is a
#      sentence naming the value and the range
#   3  the file is there and could not be read; stdout is empty. Distinct from 2, because the
#      quality gate already blocks on an unreadable tech.md, and a caller must not report it as
#      a malformed line
#
# Presence is asked on its own, with the reader's own expression: gate_steering_read returns the
# same empty string for an absent line and an empty one, and an empty one is malformed. The value
# is judged by `case` before any arithmetic touches it, because in macOS sh `$(( ))` reads `abc`
# as 0, a variable's name as that variable, `010` as octal, and runs the command inside
# `a[$(cmd)]`. Three digits at most, so the `-le` after it never meets a number it cannot hold.
gate_validator_budget() {  # <tech.md>
  _vb=$(gate_steering_read "$1" 'Validator budget'); _vbrc=$?
  [ "$_vbrc" -eq 2 ] && return 3
  if [ "$_vbrc" -eq 1 ]; then printf '%s\n' "$_gate_qg_default"; return 1; fi
  grep -q '^ *- *Validator budget:' "$1" 2>/dev/null; _vbrc=$?
  [ "$_vbrc" -eq 1 ] && { printf '%s\n' "$_gate_qg_default"; return 1; }
  [ "$_vbrc" -eq 0 ] || return 3
  # One trailing carriage return, for a tech.md saved with CRLF; then spaces and tabs, both ends.
  _vbcr=$(printf '\r'); _vbtab=$(printf '\t')
  _vb=${_vb%"$_vbcr"}
  while :; do case "$_vb" in ' '*|"$_vbtab"*) _vb=${_vb#?} ;; *) break ;; esac; done
  while :; do case "$_vb" in *' '|*"$_vbtab") _vb=${_vb%?} ;; *) break ;; esac; done
  case "$_vb" in
    [1-9]|[1-9][0-9]|[1-9][0-9][0-9])
      [ "$_vb" -le "$_gate_qg_max" ] && { printf '%s\n' "$_vb"; return 0; } ;;
  esac
  printf "the '- Validator budget:' line in %s reads '%s', and the budget is a whole number of seconds from 1 to %s, with no unit, sign, fraction or leading zero\n" "$1" "$_vb" "$_gate_qg_max"
  return 2
}

# The settings files a Claude Code launch read: the rule plugin-gate.sh's stand-down applies
# (#262), and case 263 holds the two to the same set. The wrapper keeps its own copy because it
# runs before any library is chosen. Launched below the git root, Claude Code reads the launch
# directory's settings.json and settings.local.json and the root's settings.local.json, and not
# the root's settings.json; that root is CLAUDE_PROJECT_DIR's. Without the variable, outside
# Claude Code, the git root's two files, or the working directory's with no git root. Every
# candidate is printed, there or not.
_gate_launch_settings() {
  if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    _ls_root=$(git -C "$CLAUDE_PROJECT_DIR" rev-parse --show-toplevel 2>/dev/null) || _ls_root=$CLAUDE_PROJECT_DIR
    printf '%s\n' "$CLAUDE_PROJECT_DIR/.claude/settings.json" "$CLAUDE_PROJECT_DIR/.claude/settings.local.json" \
      "$_ls_root/.claude/settings.local.json"
  else
    _ls_root=$(git rev-parse --show-toplevel 2>/dev/null) || _ls_root=$(pwd)
    printf '%s\n' "$_ls_root/.claude/settings.json" "$_ls_root/.claude/settings.local.json"
  fi
}

# Every project hook file that could have run the gate in <hooks dir>, one path per line, each
# one that exists and each once (#304, AC9). Call it before any `cd`, because CLAUDE_PROJECT_DIR
# and the working directory are the launch's:
#
#   - the settings this Claude Code launch read, above;
#   - the git root's .claude/settings.json, .claude/settings.local.json and .agents/hooks.json,
#     the working directory standing in for a root when there is none;
#   - a gate in <X>/.agents/hooks/ or <X>/.claude/hooks/: <X>'s .agents/hooks.json, or its two
#     settings files. <X> is taken from the path the gate was run through and from its physical
#     path both, so an .agents/hooks that is a symlink into a plugin checkout still finds its
#     hooks.json, and a symlinked prefix does not hide <X>.
#
# A superset, on purpose: a file this launch did not read can only lower the bound, never raise
# it. Duplicates are told apart by physical path, because macOS resolves /tmp as /private/tmp and
# git prints the second where a launch may have written the first. A path holding a newline is
# split, which is a stated residual.
gate_hook_files() {  # <hooks dir>
  _hf_root=$(git rev-parse --show-toplevel 2>/dev/null) || _hf_root=$(pwd)
  _hf_dir=$(CDPATH= cd -- "$1" 2>/dev/null && pwd) || _hf_dir=$1
  _hf_phys=$(CDPATH= cd -- "$1" 2>/dev/null && pwd -P) || _hf_phys=$1
  {
    _gate_launch_settings
    printf '%s\n' "$_hf_root/.claude/settings.json" "$_hf_root/.claude/settings.local.json" "$_hf_root/.agents/hooks.json"
    for _hf_d in "$_hf_dir" "$_hf_phys"; do
      case "$_hf_d" in
        */.agents/hooks) printf '%s\n' "${_hf_d%/hooks}/hooks.json" ;;
        */.claude/hooks) printf '%s\n' "${_hf_d%/hooks}/settings.json" "${_hf_d%/hooks}/settings.local.json" ;;
      esac
    done
  } | {
    _hf_seen=""
    while IFS= read -r _hf_f; do
      [ -e "$_hf_f" ] || continue
      _hf_k=$(CDPATH= cd -- "${_hf_f%/*}" 2>/dev/null && pwd -P) && _hf_k="$_hf_k/${_hf_f##*/}" || _hf_k=$_hf_f
      case "
$_hf_seen" in *"
$_hf_k
"*) continue ;; esac
      _hf_seen="$_hf_seen$_hf_k
"
      printf '%s\n' "$_hf_f"
    done
  }
}

# The shortest `timeout` the given hook files give the gate named <gate script>, as
# "<seconds> <file>"; "<ceiling> ceiling" when no entry names it, which covers the plugin, whose
# own hooks.json is in no project (#304, AC9). The caller keeps _gate_margin back from it.
#
# An entry names a gate when its "command" string holds the gate's file name as a whole path
# component, so `code-review-gate.sh` is not review-gate.sh. Every entry that names it counts,
# live or dead, and every `timeout` in that entry's object, a duplicate key included: each can
# only lower the bound. Status 2, with a sentence naming the file and the field, when a file is
# there and cannot be read, does not parse, or has an entry that names the gate with no integer
# `timeout` — never a default, because the harnesses' own defaults are not something this
# project measured — and when the shortest timeout leaves nothing once the margin is kept back.
#
# The scan is a string-aware tokenizer in POSIX awk, not a line or brace count: a minified file
# is one line, a fast check's command holds `{}`, and a settings file may carry `//` and `/* */`
# comments. Its input is folded into 512-byte records first, newlines kept as \001, and its state
# (inside a string, an escape pending, the depth, each open object's keys) carries from one record
# to the next. So it is linear in the file's size: a tokenizer that indexes one long line with
# `substr` is quadratic in BWK awk, measured at 8.5 s for 749 KB, and the scan runs inside the
# margin. LC_ALL=C on all three stages, so they count bytes: BSD tr in a UTF-8 locale stops at
# a byte that is not UTF-8, and a hook file read as cut off there would block every turn. A
# pipeline is safe here only because the tokenizer demands a whole top-level value: a read that
# failed or stopped short, or an awk that printed nothing, is a file that does not parse. A
# timeout past nine digits reads as 999999999, which no budget reaches and the shell's `-lt` can
# hold.
# That tokenizer, as one program both hook-file readers run: `mode=timeout` for gate_hook_timeout,
# `mode=switches` for gate_hook_switches below (#330). Only the two modes' own lines differ, so the
# readers cannot disagree about what a file says. It is awk, whose `$0` is its own, not the shell's.
# shellcheck disable=SC2016
_gate_hook_scan='
      function fail(why) { if (err == "") err = why " near byte " pos }
      function namech(c) { return c ~ /[A-Za-z0-9._-]/ }
      function names(s, g,   p, off) {
        off = 0
        while (g != "" && (p = index(substr(s, off + 1), g)) > 0) {
          p += off
          if (!namech(p > 1 ? substr(s, p - 1, 1) : "") && !namech(substr(s, p + length(g), 1))) return 1
          off = p
        }
        return 0
      }
      function value(kind, text,   sg) {
        fresh = 0
        if (depth == 0) { want = "end"; return }
        want = "sep"
        if (type[depth] != "o") return
        if (mode == "switches") {
          # A group is a member of the top-level object; its `enabled` is at depth 2, and
          # anything but the literal true is off. A gate counts wherever its group nests it.
          if (depth == 2 && type[1] == "o" && key[2] == "enabled" && !(kind == "l" && text == "true")) off[key[1]] = 1
          if (depth >= 2 && type[1] == "o" && key[depth] == "command" && kind == "s") {
            if (names(text, "quality-gate.sh")) { runs[key[1], "quality-gate.sh"] = 1; grp[key[1]] = 1 }
            if (names(text, "review-gate.sh")) { runs[key[1], "review-gate.sh"] = 1; grp[key[1]] = 1 }
          }
          return
        }
        if (key[depth] == "command" && kind == "s" && names(text, g)) named[depth] = 1
        if (key[depth] != "timeout") return
        if (kind != "n" || text !~ /^-?(0|[1-9][0-9]*)$/) { tbad[depth] = 1; return }
        sg = ""; if (substr(text, 1, 1) == "-") { sg = "-"; text = substr(text, 2) }
        if (length(text) > 9) text = "999999999"
        text = sg text
        if (!(depth in tmin) || text + 0 < tmin[depth] + 0) tmin[depth] = text
      }
      function bare_end() {
        if (bare == "") return
        if (bare == "true" || bare == "false" || bare == "null") value("l", bare)
        else if (bare ~ /^-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][-+]?[0-9]+)?$/) value("n", bare)
        else fail("a bare word that is no JSON value")
        bare = ""
      }
      function push(c) {
        if (want != "value") { fail("an unexpected " c); return }
        depth++; type[depth] = (c == "{") ? "o" : "a"; key[depth] = ""; named[depth] = 0; tbad[depth] = 0
        delete tmin[depth]
        want = (c == "{") ? "key" : "value"; fresh = 1
      }
      function pop(c) {
        if (depth == 0 || (c == "}") != (type[depth] == "o")) { fail("an unmatched " c); return }
        if (want != "sep" && !fresh) { fail("a " c " where a value was due"); return }
        if (type[depth] == "o" && named[depth]) {
          if (tbad[depth] || !(depth in tmin)) notime = 1
          else if (best == "" || tmin[depth] + 0 < best + 0) best = tmin[depth]
        }
        depth--
        value("c", "")
      }
      function string_end() {
        if (iskey) { key[depth] = sbuf; want = "colon"; fresh = 0 }
        else value("s", sbuf)
      }
      BEGIN { NL = sprintf("%c", 1); want = "value"; best = "" }
      err != "" { next }
      {
        rec = $0; n = length(rec); i = 1
        while (i <= n && err == "") {
          if (instr && esc) {
            c = substr(rec, i, 1); i++; pos++
            if (uleft) {
              h = index("0123456789abcdef", tolower(c))
              if (!h) { fail("a broken \\u escape"); continue }
              ucode = ucode * 16 + h - 1
              if (--uleft == 0) { esc = 0; if (keep) sbuf = sbuf ((ucode > 0 && ucode < 128) ? sprintf("%c", ucode) : "?") }
              continue
            }
            if (c == "u") { uleft = 4; ucode = 0; continue }
            esc = 0
            if (!index("\"\\/bfnrt", c)) { fail("a broken escape"); continue }
            if (keep) sbuf = sbuf (index("bfnrt", c) ? " " : c)
            continue
          }
          if (instr) {
            rest = substr(rec, i)
            j = index(rest, "\""); b = index(rest, "\\"); m = index(rest, NL)
            if (b && (!j || b < j)) j = b
            if (m && (!j || m < j)) j = m
            if (!j) { if (keep) sbuf = sbuf rest; pos += n - i + 1; i = n + 1; continue }
            if (keep) sbuf = sbuf substr(rest, 1, j - 1)
            c = substr(rest, j, 1); i += j; pos += j
            if (c == NL) fail("a line break inside a string")
            else if (c == "\\") esc = 1
            else { instr = 0; string_end() }
            continue
          }
          if (cmt == 1) {
            m = index(substr(rec, i), NL)
            if (!m) { pos += n - i + 1; i = n + 1 } else { i += m; pos += m; cmt = 0 }
            continue
          }
          if (cmt == 2) {
            if (star) { star = 0; if (substr(rec, i, 1) == "/") { i++; pos++; cmt = 0; continue } }
            m = index(substr(rec, i), "*")
            if (!m) { pos += n - i + 1; i = n + 1 } else { i += m; pos += m; star = 1 }
            continue
          }
          c = substr(rec, i, 1); i++; pos++
          if (slash) {
            slash = 0
            if (c == "/") { cmt = 1; continue }
            if (c == "*") { cmt = 2; star = 0; continue }
            fail("a / that opens no comment"); continue
          }
          if (c == " " || c == "\t" || c == "\r" || c == NL) { bare_end(); continue }
          if (c == "/") { bare_end(); slash = 1; continue }
          if (c == "\"") {
            bare_end()
            if (want == "key") { iskey = 1; keep = 1 }
            else if (want == "value") { iskey = 0; keep = (depth > 0 && type[depth] == "o" && key[depth] == "command") }
            else { fail("an unexpected string"); continue }
            instr = 1; sbuf = ""; continue
          }
          if (c == "{" || c == "[") { bare_end(); push(c); continue }
          if (c == "}" || c == "]") { bare_end(); pop(c); continue }
          if (c == ":") { bare_end(); if (want != "colon") fail("an unexpected :"); else want = "value"; continue }
          if (c == ",") {
            bare_end()
            if (want != "sep" || depth == 0) fail("an unexpected ,")
            else want = (type[depth] == "o") ? "key" : "value"
            continue
          }
          if (bare == "" && want != "value") { fail("unexpected text"); continue }
          bare = bare c
        }
      }
      END {
        if (err == "") bare_end()
        if (err == "") {
          if (instr) fail("a string never closed")
          else if (cmt == 2) fail("a comment never closed")
          else if (slash) fail("a / that opens no comment")
          else if (depth > 0) fail("a { or [ never closed")
          else if (want != "end") fail("no JSON value")
        }
        if (err != "") print "err " err
        else if (mode == "switches") {
          for (k in grp) {
            gs = ""
            if ((k, "quality-gate.sh") in runs) gs = "quality-gate.sh"
            if ((k, "review-gate.sh") in runs) gs = gs (gs == "" ? "" : " and ") "review-gate.sh"
            if (k in off) print "off\t" gs "\t" k
            else { if ((k, "quality-gate.sh") in runs) onq = 1; if ((k, "review-gate.sh") in runs) onr = 1 }
          }
          if (onq && !onr) print "one\tquality-gate.sh\treview-gate.sh"
          if (onr && !onq) print "one\treview-gate.sh\tquality-gate.sh"
          print "done"
        }
        else if (notime) print "notime"
        else print "ok" (best == "" ? "" : " " best)
      }
'
gate_hook_timeout() {  # <gate script> <ceiling> <file>...
  _ht_gate=$1; _ht_lo=$2; _ht_src=ceiling; shift 2
  for _ht_f in "$@"; do
    if [ ! -f "$_ht_f" ] || [ ! -r "$_ht_f" ]; then
      printf '%s exists and cannot be read, so the "timeout" it gives %s is unknown\n' "$_ht_f" "$_ht_gate"
      return 2
    fi
    _ht_r=$(LC_ALL=C tr '\n' '\001' < "$_ht_f" | LC_ALL=C fold -b -w 512 | LC_ALL=C awk -v g="$_ht_gate" -v mode=timeout "$_gate_hook_scan")
    case "$_ht_r" in
      ok) ;;
      'ok '*)
        _ht_t=${_ht_r#ok }
        if [ "$_ht_src" = ceiling ] || [ "$_ht_t" -lt "$_ht_lo" ]; then _ht_lo=$_ht_t; _ht_src=$_ht_f; fi ;;
      notime)
        printf '%s has an entry whose "command" runs %s and that has no integer "timeout", so the time the harness gives it is unknown; give that entry a "timeout" in whole seconds\n' "$_ht_f" "$_ht_gate"
        return 2 ;;
      'err '*)
        printf '%s does not parse as JSON (%s), so the "timeout" it gives %s is unknown\n' "$_ht_f" "${_ht_r#err }" "$_ht_gate"
        return 2 ;;
      *)
        printf '%s could not be scanned for the "timeout" it gives %s: the scan printed no answer\n' "$_ht_f" "$_ht_gate"
        return 2 ;;
    esac
  done
  if [ "$_ht_src" != ceiling ] && [ "$_ht_lo" -le "$_gate_margin" ]; then
    printf '%s gives %s a "timeout" of %s s, which leaves no time once the gate keeps its %s s margin back to write a verdict; raise that "timeout"\n' "$_ht_src" "$_ht_gate" "$_ht_lo" "$_gate_margin"
    return 2
  fi
  printf '%s %s\n' "$_ht_lo" "$_ht_src"
}

# Each thing in one hook file that switches a gate off, one sentence a line (#330, #324 AC5).
# Antigravity's `enabled` belongs to a named group, and a group whose `enabled` is not the literal
# true runs none of its entries, so the gates it holds stop with no message. Read fail-closed:
# `false`, `"false"`, 0 and null are all off, since what Antigravity makes of a non-boolean was
# never measured. Also a file whose enabled groups run one of the two gates and not the other. A
# file that runs neither gate is not judged: nothing here can tell it from a project's own
# Antigravity hooks. Status 0 with nothing printed when nothing is off, 1 when something is, and 2
# with a sentence when the file cannot be read or does not parse.
gate_hook_switches() {  # <file>
  _hs_f=$1
  if [ ! -f "$_hs_f" ] || [ ! -r "$_hs_f" ]; then
    printf '%s exists and cannot be read, so whether it switches a gate off is unknown\n' "$_hs_f"
    return 2
  fi
  _hs_r=$(LC_ALL=C tr '\n' '\001' < "$_hs_f" | LC_ALL=C fold -b -w 512 | LC_ALL=C awk -v g= -v mode=switches "$_gate_hook_scan")
  case "$_hs_r" in
    'err '*)
      printf '%s does not parse as JSON (%s), so whether it switches a gate off is unknown\n' "$_hs_f" "${_hs_r#err }"
      return 2 ;;
    done) return 0 ;;
    *"
done") ;;
    *)
      printf '%s could not be scanned for its switches: the scan printed no answer\n' "$_hs_f"
      return 2 ;;
  esac
  _hs_tab=$(printf '\t')
  printf '%s\n' "${_hs_r%"
done"}" | while IFS=$_hs_tab read -r _hs_kind _hs_a _hs_b; do
    case "$_hs_kind" in
      off) printf '%s: the group "%s" runs %s, and its "enabled" is not true, so Antigravity runs none of it; set it to true\n' "$_hs_f" "$_hs_b" "$_hs_a" ;;
      one) printf '%s: %s runs and %s does not, so that gate never runs on this project; restore its entry as init renders it\n' "$_hs_f" "$_hs_a" "$_hs_b" ;;
    esac
  done
  return 1
}

# Run <command> as the gate's child, bounded by <budget> seconds, and return its status (#304).
#
# The bound is one watchdog, started before the child and confirmed armed before the child
# starts. Its deadline is a `sleep`, a relative interval that setting the clock does not move,
# where a wall-clock deadline moves with an NTP step or a VM resume. The child runs in the
# foreground, so a validator keeps the hook's stdin and today's signal dispositions; a background
# job would inherit SIGINT and SIGQUIT ignored, which macOS sh and dash cannot restore.
#
# What the child leaves in <run dir>, for gate_replay and the gate's own blocks:
#
#   ppid     the shell that forked the child, written first, which is the parent the watchdog
#            looks for: $$ would name the gate, and not the subshell, when this runs in one
#   pid      the child's pid, written next, before any gate code runs; `exec` keeps it, so it is
#            the child's own. A child that cannot write both exits 125 without running anything,
#            since a command with no pid on disk is one the watchdog cannot kill
#   verdict  its stdout, which only gate_pass or a block writes: one line or nothing
#   err      its stderr
#   end      its verdict is whole (gate_pass and _gate_block_exit write it)
#
# and the watchdog: `armed` once its deadline runs, `fired` when the deadline passed, and
# `nowalk` when it could not walk the child's tree and killed the child alone. The gate writes
# `done`, the only thing that disarms the watchdog.
#
# Every marker is written with `printf ''`, never `:`. A redirection that fails on `:`, a special
# builtin, exits a POSIX shell whatever wraps it, so a run dir a validator removed or made
# unwritable would end the gate after its child with nothing on stdout, and end the watchdog at
# `fired` before its kill: both a pass where a block was due. A marker that cannot be written is
# only missing, which costs the budget's latency or a line of the block, never the block itself.
#
# Inside `{ …; } 2>/dev/null`, with the status captured inside the braces: without it, bash as sh
# prints `Terminated: 15` for a killed child onto the gate's own stderr, which is Claude Code's
# block reason. The watchdog signals the child only while `ps` lists it under the parent in
# `ppid`, which is how a pid the gate has already reaped, and the system has reused, is never
# signalled.
#
# <run dir> must be absolute, and a relative one blocks before anything starts: the child writes
# `end` after it has cd'd to the git root, and neither the parent nor the watchdog ever cds.
#
# Every return path reaps the watchdog, looping while `kill -0` still reaches it because a
# trapped signal returns `wait` early: once the deadline fired the watchdog is finishing its kill,
# and the gate waits for that, so nothing it killed is still alive when the gate decides. A
# watchdog that does not confirm it is armed is STOPped, its children (its sleep, which ignores
# every catchable signal) KILLed from a snapshot, and then it is KILLed itself: all safe, because
# it is this shell's own unreaped child and cannot reap its own while stopped. The gate then
# blocks without running the check (AC5).
# shellcheck disable=SC2086  # $_gb_k is a list of pids, one per word
gate_bounded() {  # <budget> <run dir> <command>...
  _gb_run=$2
  case "$_gb_run" in
    /*) ;;
    *)
      trap '' HUP INT QUIT TERM USR1 USR2 ALRM
      gate_block "${_gate_name:-Gate}: the directory this check runs in, '$_gb_run', is not an absolute path, so the check had no deadline it could be held to and was not run. A check the harness kills at its timeout ends the turn as a pass, so this blocks instead. Set TMPDIR to an absolute path, or unset it." ;;
  esac
  _gate_watchdog "$1" "$2" </dev/null >/dev/null 2>&1 &
  _gb_wd=$!
  shift 2
  if ! _gate_await "$_gb_run/armed" 100 2; then
    { kill -s STOP "$_gb_wd"; } 2>/dev/null
    if _gate_snapshot; then
      _gb_k=$(printf '%s\n' "$_wd_ps" | awk -v w="$_gb_wd" '$2 == w { print $1 }')
      [ -z "$_gb_k" ] || { kill -s KILL $_gb_k; } 2>/dev/null
    fi
    { kill -s KILL "$_gb_wd"; } 2>/dev/null
    _gate_reap "$_gb_wd"
    trap '' HUP INT QUIT TERM USR1 USR2 ALRM
    gate_block "${_gate_name:-Gate}: the watchdog that bounds this check did not confirm it was armed (no 'armed' in $_gb_run), so the check had no deadline and was not run. A check the harness kills at its timeout ends the turn as a pass, so this blocks instead. Run again; if this repeats, check that the gate's temporary directory is writable."
  fi
  { sh -c 'echo $PPID >"$1/ppid" && echo $$ >"$1/pid" || exit 125; shift; exec "$@"' _ "$_gb_run" "$@" >"$_gb_run/verdict" 2>"$_gb_run/err"; _gb_rc=$?; } 2>/dev/null
  if [ ! -e "$_gb_run/fired" ]; then
    { printf '' > "$_gb_run/done"; } 2>/dev/null
    { kill -s USR1 "$_gb_wd"; } 2>/dev/null
  fi
  _gate_reap "$_gb_wd"
  return "$_gb_rc"
}

# Wait up to <hundredths> polls of 0.01 s for <file> to be there and not empty, or up to <seconds>
# polls of 1 s where `sleep` takes no fraction. 1 when the polls run out. A sleep that fails is
# taken for one that rejects a fraction, which only makes the wait coarser. Hundredths, because
# what it waits for is written within milliseconds, and every gate run pays the first poll.
_gate_await() {  # <file> <hundredths> <seconds>
  _aw_n=0; _aw_max=$2; _aw_s=0.01
  while [ ! -s "$1" ]; do
    [ "$_aw_n" -lt "$_aw_max" ] || return 1
    if sleep "$_aw_s" 2>/dev/null || [ "$_aw_s" = 1 ]; then
      _aw_n=$((_aw_n + 1))
    else
      _aw_s=1; _aw_max=$3; _aw_n=0
    fi
  done
}

# Reap a background child of this shell, however many trapped signals cut `wait` short. 127 is
# `wait` saying the pid is no child of this shell, which ends the loop rather than spin on a pid
# the system has handed to someone else.
_gate_reap() {  # <pid>
  while kill -0 "$1" 2>/dev/null; do
    { wait "$1"; } 2>/dev/null
    [ "$?" -ne 127 ] || break
  done
}

# Each live pid among its arguments, space-separated.
_gate_alive() {  # <pid>...
  for _al_p in "$@"; do kill -0 "$_al_p" 2>/dev/null && printf '%s ' "$_al_p"; done
}

# Every process as "<pid> <ppid>", in $_wd_ps; 1 when `ps` exits non-zero or prints nothing. On a
# line of its own and never a pipeline, whose status would be its last command's: a `ps` that
# failed would read as a table with nothing in it. The watchdog's only call to `ps`.
_gate_snapshot() {
  _wd_ps=$(ps -A -o pid= -o ppid= 2>/dev/null) && [ -n "$_wd_ps" ]
}

# The descendants of <pid>... in a _gate_snapshot table on stdin, one per line, each
# once, never a root.
_gate_descendants() {  # <pid>...
  awk -v roots="$*" '
    { kids[$2] = kids[$2] " " $1 }
    END {
      n = split(roots, q, " "); for (i = 1; i <= n; i++) seen[q[i]] = 1
      for (h = 1; h <= n; h++) {
        m = split(kids[q[h]], c, " ")
        for (j = 1; j <= m; j++) if (!(c[j] in seen)) { seen[c[j]] = 1; q[++n] = c[j]; print c[j] }
      }
    }'
}

# gate_bounded's watchdog, run in a background subshell with its descriptors on /dev/null.
#
# Nothing a validator can send to its process group ends it or disarms it. It ignores HUP, INT,
# QUIT, TERM, USR2 and ALRM, and USR1 too until its sleep is running, so the sleep is born
# ignoring all seven; then USR1 is trapped to a no-op, which only interrupts `wait` so the
# watchdog looks for `done`. Disarming needs that file, which only the gate writes, so a
# validator's `kill -s USR1 0` makes it look and find nothing. It looks before each `wait` as
# well as after, so a `done` and USR1 that land before the first `wait` are not lost; the window
# left is two builtins wide, and missing it costs the gate the budget's latency, never its verdict.
#
# When the sleep ends it fires: it ignores USR1, checks `done` one last time, writes `fired`, and
# kills the child's tree. The walk is rooted at the child, never at the gate, so the watchdog is
# never in it and needs no pid of its own:
#
#   1. the child's pid from `pid`, polling up to 1 s, and its parent from `ppid`; with neither the
#      child never ran, so there is nothing to kill. Then a `ps -A -o pid= -o ppid=` snapshot on a
#      line of its own, never a pipeline, whose status would be awk's
#   2. the child is signalled only while the snapshot lists it under that parent; a child listed
#      under another parent is a pid the gate reaped and the system reused. A walk
#      has failed when `ps` exits non-zero, prints nothing, or leaves out a child that `kill -0`
#      still reaches: the set is then the child alone, and `nowalk` says so
#   3. STOP the child, then walk and STOP its descendants until the set stops growing, at most
#      five times; TERM the set, then CONT, so every member meets the TERM at once
#   4. poll `kill -0` once a second for up to 2 s, stopping as soon as nothing is left: whole
#      seconds, so a `sleep` without fractions changes nothing
#   5. STOP whatever in the saved set is still alive, walk again from those pids, adding and
#      STOPping what it finds until the set stops growing (at most five times), and KILL the
#      union. Rooted at the saved pids, so a descendant already reparented to pid 1 is still
#      covered, and a worker that a TERM-catching loop forked during the grace is found from it.
# shellcheck disable=SC2086  # $_wd_set is a list of pids, one per word
_gate_watchdog() {  # <budget> <run dir>
  unset IFS
  trap '' HUP INT QUIT TERM USR1 USR2 ALRM
  (trap '' USR1; exec sleep "$1") &
  _wd_sl=$!
  trap ':' USR1
  if ! { echo armed > "$2/armed"; } 2>/dev/null; then
    kill -s KILL "$_wd_sl" 2>/dev/null; wait "$_wd_sl"; exit 1
  fi
  while :; do
    if [ -e "$2/done" ]; then kill -s KILL "$_wd_sl" 2>/dev/null; wait "$_wd_sl"; exit 0; fi
    wait "$_wd_sl"
    kill -0 "$_wd_sl" 2>/dev/null || break
  done
  trap '' USR1
  [ -e "$2/done" ] && exit 0
  { printf '' > "$2/fired"; } 2>/dev/null

  _gate_await "$2/pid" 100 1
  _wd_c=$(cat "$2/pid" 2>/dev/null); _wd_g=$(cat "$2/ppid" 2>/dev/null)
  case "$_wd_c:$_wd_g" in *:|:*|*[!0-9:]*) exit 0 ;; esac
  _wd_walk=no; _wd_pp=""
  if _gate_snapshot; then
    _wd_pp=$(printf '%s\n' "$_wd_ps" | awk -v c="$_wd_c" '$1 == c { print $2; exit }')
  fi
  if [ -n "$_wd_pp" ]; then
    [ "$_wd_pp" = "$_wd_g" ] || exit 0
    _wd_walk=yes
  else
    kill -0 "$_wd_c" 2>/dev/null || exit 0
    { printf '' > "$2/nowalk"; } 2>/dev/null
  fi

  _wd_set=$_wd_c
  kill -s STOP $_wd_set 2>/dev/null
  _gate_watchdog_walk "$2"
  kill -s TERM $_wd_set 2>/dev/null
  kill -s CONT $_wd_set 2>/dev/null
  _wd_i=0
  while [ "$_wd_i" -lt 2 ] && [ -n "$(_gate_alive $_wd_set)" ]; do
    sleep 1; _wd_i=$((_wd_i + 1))
  done

  _wd_set=$(_gate_alive $_wd_set)
  [ -n "$_wd_set" ] || exit 0
  kill -s STOP $_wd_set 2>/dev/null
  _gate_watchdog_walk "$2"
  kill -s KILL $_wd_set 2>/dev/null
  exit 0
}

# Steps 3 and 5's walk: grow $_wd_set by the descendants a fresh snapshot shows, STOPping each as
# it is found, until a round finds nothing, at most five rounds. Only after a first walk that
# found the child, since a `ps` that failed or lied once is not asked again.
# shellcheck disable=SC2086  # $_wd_set and $_ww_new are lists of pids, one per word
_gate_watchdog_walk() {  # <run dir>
  [ "$_wd_walk" = yes ] || return 0
  _ww_i=0
  while [ "$_ww_i" -lt 5 ]; do
    _ww_i=$((_ww_i + 1))
    _gate_snapshot || { { printf '' > "$1/nowalk"; } 2>/dev/null; return 0; }
    _ww_new=$(printf '%s\n' "$_wd_ps" | _gate_descendants $_wd_set)
    [ -n "$_ww_new" ] || return 0
    kill -s STOP $_ww_new 2>/dev/null
    _wd_set="$_wd_set $_ww_new"
  done
}

# Judge what a bounded child left in <run dir>, given the status gate_bounded returned (#304).
# Only once the child wrote `end`: gate_pass and _gate_block_exit write it after their output, so
# a verdict torn by a kill is never judged, whatever its bytes. And never once the gate caught a
# signal, which it records in `signalled`.
#
#   - `verdict` exactly `{}` with status 0 is a pass: the child's stderr is replayed and the gate
#     passes;
#   - one line that opens `{"decision":"continue","reason":"` and closes `"}`, with the status the
#     channel gives a block, is that block: both files replayed, and out through _gate_block_exit.
#
# Anything else returns 1 having written nothing, and the gate builds a block of its own; so does
# a call with no status, read as `${2-}` because a gate under `set -u` must not abort with nothing
# on stdout, which a harness reads as a pass. A
# recognised verdict wins even beside `fired`: the child reached it within the budget and a moment.
gate_replay() {  # <run dir> <the child's status>
  [ -e "$1/end" ] && [ ! -e "$1/signalled" ] || return 1
  _rp_v=$(cat -- "$1/verdict" 2>/dev/null) || return 1
  case "$_rp_v" in *'
'*) return 1 ;; esac
  printf '%s\n' "$_rp_v" | cmp -s - "$1/verdict" || return 1
  if [ "$_rp_v" = '{}' ] && [ "${2-}" = 0 ]; then
    cat -- "$1/err" >&2 2>/dev/null
    gate_pass
  fi
  case "$_rp_v" in '{"decision":"continue","reason":"'*'"}') ;; *) return 1 ;; esac
  _gate_block_status
  [ "${2-}" = "$?" ] || return 1
  printf '%s\n' "$_rp_v"
  cat -- "$1/err" >&2 2>/dev/null
  _gate_block_exit
}

# Emit a spec's Tasks section ONLY — section 3, up to the next heading.
#
# The scoping is the load-bearing part. Acceptance criteria are checkboxes too, and on a
# shipped spec they are commonly left unticked; counting those as open work would make the
# gate fire forever on every finished spec, which is how a gate earns being switched off.
# Both counters below scope through here so they can never disagree about what a task is.
#
# Text in rather than a path, because since #26 the same reading has to serve two sources: a
# file in the working tree, and a blob on a branch nobody is standing on. The file wrappers
# below keep every existing caller unchanged.
_gate_tasks_section_text() {
  printf '%s\n' "$1" | awk '/^#+ *3\./ {f=1; next} /^#+ /{f=0} f'
}

# Count UNTICKED checkboxes: how much work is left.
gate_open_tasks_text() {
  _gate_tasks_section_text "$1" | grep -c '^ *- \[ \]'
}

# Count ALL checkboxes in a spec's Tasks section, ticked or not.
#
# gate_open_tasks returning 0 is ambiguous, and the two meanings are opposites: "every task
# is done" and "no task was ever written". Reading the second as the first blocks a spec that
# is still being drafted, which is the state `spec` step 3 tells the author to create. A
# caller needs both counts to tell them apart.
gate_total_tasks_text() {
  _gate_tasks_section_text "$1" | grep -c '^ *- \[[ xX]\]'
}

# The file forms, kept because a project's own scripts may source this library and ask about a
# spec on disk; the private section wrapper went with #26, having lost its last caller.
# An unreadable or absent file yields empty text and therefore zero, which is
# the reading `review-gate.sh` already depends on and which #8 and its AC7 pinned: zero total
# means "nothing authored", and telling that apart from "cannot be read" is the CALLER's job,
# done before it counts anything.
gate_open_tasks()     { gate_open_tasks_text     "$(cat -- "$1" 2>/dev/null)"; }
gate_total_tasks()    { gate_total_tasks_text    "$(cat -- "$1" 2>/dev/null)"; }

# Which branch HEAD is on, by its own name. The name match gate_branch_specs reads is this name;
# the specs a branch adds are found whatever it is called (#316).
#
# Asked of the FULL ref and stripped by hand, never of a short form. Git shortens a ref only as
# far as stays unambiguous, so a branch that shares its name with a tag, or a branch named
# `origin` beside `refs/remotes/origin/HEAD`, comes back from `symbolic-ref --short`,
# `rev-parse --abbrev-ref` and `%(refname:short)` as `heads/<name>` — and every caller used that
# string as the slug, read `.specs/heads/<name>/`, found nothing, and passed. #233.
#
#   0    a branch, born or unborn; stdout is its name
#   1    no branch: a detached HEAD, or HEAD pointed outside refs/heads/ by plumbing
#        (`git symbolic-ref HEAD refs/tags/x`), which is detached in every sense a gate needs
#   128  git's own status when it cannot read the ref store; the caller says what that means
#
# The statuses are #228's, so review-gate.sh's three arms read through here unchanged.
gate_head_branch() {
  _hb=$(git symbolic-ref -q HEAD 2>/dev/null); _hbrc=$?
  [ "$_hbrc" -eq 0 ] || return "$_hbrc"
  case "$_hb" in
    refs/heads/*) printf '%s\n' "${_hb#refs/heads/}" ;;
    *) return 1 ;;
  esac
}

# The commit a full refname points at, or nothing, exactly.
#
# A full refname is not enough on its own: `rev-parse` disambiguates it like any other name, so
# with no `main` branch `refs/heads/main` resolves a tag literally named `refs/heads/main`
# (`refs/tags/refs/heads/main`). `show-ref --verify` matches only the exact ref, and follows a
# symbolic one, so `refs/remotes/origin/HEAD` still resolves; once it has said the ref exists,
# `rev-parse` takes that ref first. Case 183 goes red without the first line. #233.
gate_ref_commit() {  # <full refname>
  git show-ref --verify -q "$1" 2>/dev/null || return 1
  git rev-parse --verify -q "$1^{commit}" 2>/dev/null
}

# Does <ref>'s tree name <path>? Asked of the tree, never of the object behind the name.
#
# This used to be asked as `git cat-file -e <ref>:<path>`, which is two questions with one
# status between them: whether the tree names the path, and whether the object it names is in
# this repository. Every reader took the non-zero status as "no spec", so a spec whose blob git
# could not get — a partial clone that cannot reach its remote, or a damaged object store — was
# a branch with nothing to review. #191.
#
#   0  the tree names the path
#   1  the tree was read, and does not
#   2  git could not read the tree: any other status from `ls-tree`
#
# `ls-tree` rather than `rev-parse --verify -q <ref>:<path>`, which the issue's triage measured
# for the blob and which is blind one level up: with a tree object on the way to the path gone
# it exits 1 and prints nothing, exactly as for a path that is not there, where `ls-tree` exits
# non-zero. Case 194. It reads trees only, so in a blobless clone it answers offline and fetches
# nothing. `--full-tree` because without it the path is relative to the working directory.
#
# A ref with no commit is a 2, not a 1: `ls-tree` cannot tell an unborn HEAD from a ref it could
# not read. The one caller that can stand on an unborn branch rules that out before asking.
gate_tree_names() {  # <ref> <path from the repository root>
  _tn=$(git ls-tree --full-tree "$1" -- "$2" 2>/dev/null) || return 2
  [ -n "$_tn" ]
}

# The commits the gates measure a branch against: what has shipped. One list, read by the review
# gate, the digest and check-unreviewed-work.sh, which used to keep it inline in the gate alone
# (#316). gate_default_bases prints every candidate that resolves, space-separated, for the specs
# a branch adds; gate_default_base the first, for the shipped skip.
#
# The list is longer since #26 widened the scan, because an unresolvable base costs far more than
# it used to. It used to mean one false block, while you stood on your own merged branch; now it
# means the merged check never fires for ANY branch, so every shipped but undeleted spec branch
# blocks every turn from everywhere. `master` is the common case that was missing, and a
# repository with no remote at all has no origin/* to fall back on.
#
# Each candidate is a full refname, resolved exactly. These used to be bare names, and git
# resolves a bare name to a tag before a branch or a remote, so `git tag main <unreviewed tip>`
# made that tip the base and the scan skipped its branch as shipped. #233, cases 181–183.
gate_default_bases() {
  _dbs=''
  for _dbr in refs/remotes/origin/HEAD refs/remotes/origin/main refs/remotes/origin/master \
              refs/heads/main refs/heads/master; do
    _dbc=$(gate_ref_commit "$_dbr") && _dbs="$_dbs${_dbs:+ }$_dbc"
  done
  [ -n "$_dbs" ] || return 1
  printf '%s\n' "$_dbs"
}

gate_default_base() {
  _db=$(gate_default_bases) || return 1
  printf '%s\n' "${_db%% *}"
}

# Which specs a branch carries. The one place a reader turns a branch into spec directories, and a
# shape case in test-gates.sh fails if a reader composes `.specs/<branch>` anywhere else. #316.
#
# The flow names a branch and its spec directory alike (`spec` step 1), and every reader used to
# take that convention as the address. A branch named any other way — `feature/12-x`, a typo, a
# spec archived on its own branch — asked for a path that did not exist, `_gate_read` answered
# "absent", and absent is "nothing to demand". So the list is a union of two readings, and a union
# checks at least what either does:
#
#   the name match   `.specs/<branch>`, unless the tree read was read and does not name its
#                    spec.md. Today's reading, kept so that no reader checks less than it did
#   the adds         every spec.md the branch ADDS against its merge base, under `.specs/` or
#                    `.specs/_archive/`, except one whose slug the merge base already carries in
#                    either place. A spec the base had and the branch moved is therefore not the
#                    branch's, so an `archive` sweep adds nothing; one the branch only edited is
#                    no add at all (the spec's Q1)
#
# The adds are asked with `--no-renames`, and the slug test does the work rename detection was
# first asked to do. Git pairs a deleted file with an added one at 50% similarity, every spec
# shares the template's headings, and a branch that deleted a shipped spec and added a finished
# look-alike lost the new one to the pairing (review round 1, case 373).
#
# The merge base is one call against every base given: `git merge-base <tip> <base>...` is the
# latest point where the tip meets any of them. The first candidate alone lagged whenever a local
# `main` was ahead of its remote-tracking ref, and every spec merged in between became the
# branch's own (case 374). Nothing is derived when that point is the tip itself: the base branch,
# a branch with no commit of its own, or one already in a local candidate, each of which the
# callers skip as shipped. The cost of that, said once: an unreviewed branch not named for its spec,
# merged into a local `main` and not pushed, is silent locally, as it was before #316.
#
# Prints one directory per line, such as `.specs/12-x` or `.specs/_archive/12-x`.
#
#   0  the list is complete
#   2  git could not list the adds. What the name match found is printed all the same, so the
#      caller still judges it, and blocks besides: a listing that failed is never "no spec"
#
# <tip> empty is the working tree, which #26 counts, and three lists: committed adds from the merge
# base to HEAD, which is what #177 reads when the working tree lacks a committed spec; adds from the
# merge base to the working tree; and untracked spec files that .gitignore does not exclude. <bases>
# empty is the name match alone, which is what a caller passes for no resolvable base, a detached
# HEAD or an unborn branch.
#
# No merge base at all, an orphan branch, is `git merge-base` exiting 1 having printed nothing, and
# the adds are then read against the empty tree. Every other failure is a 2.
gate_branch_specs() {  # <base shas, space-separated, empty for none> <tip sha, empty for the working tree> <branch name>
  _sbases=$1; _stip=$2; _sname=$3
  _sdir=".specs/$_sname"
  _slist=''; _sfail=0
  if [ -n "$_stip" ]; then
    _shead=$_stip
    gate_tree_names "$_stip" "$_sdir/spec.md"; [ "$?" -eq 1 ] || _slist=$_sdir
  else
    _shead=$(git rev-parse --verify -q HEAD 2>/dev/null) || _shead=''
    if [ -f "$_sdir/spec.md" ]; then
      _slist=$_sdir
    elif [ -n "$_shead" ]; then
      gate_tree_names HEAD "$_sdir/spec.md"; [ "$?" -eq 1 ] || _slist=$_sdir
    fi
  fi

  if [ -n "$_sbases" ] && [ -n "$_shead" ]; then
    # shellcheck disable=SC2086  # deliberate word-split: one commit sha per argument, and a sha holds no space or glob
    _smb=$(git merge-base "$_shead" $_sbases 2>/dev/null); _src=$?
    if [ "$_src" -eq 1 ] && [ -z "$_smb" ]; then
      _smb=$(git hash-object -t tree /dev/null 2>/dev/null) || _sfail=2
    elif [ "$_src" -ne 0 ] || [ -z "$_smb" ]; then
      _sfail=2
    fi
    _sadds=''
    if [ "$_sfail" -eq 0 ] && [ "$_smb" != "$_shead" ]; then
      _sadd=$(_gate_spec_adds git diff --no-ext-diff --no-color --no-renames --name-only --diff-filter=A -z "$_smb" "$_shead" -- .specs/) || _sfail=2
      [ "$_sfail" -ne 0 ] || _sadds=$_sadd
      if [ -z "$_stip" ] && [ "$_sfail" -eq 0 ]; then
        _sadd=$(_gate_spec_adds git diff --no-ext-diff --no-color --no-renames --name-only --diff-filter=A -z "$_smb" -- .specs/) || _sfail=2
        [ "$_sfail" -ne 0 ] || _sadds="$_sadds
$_sadd"
      fi
      if [ -z "$_stip" ] && [ "$_sfail" -eq 0 ]; then
        _sadd=$(_gate_spec_adds git ls-files --others --exclude-standard -z -- .specs/) || _sfail=2
        [ "$_sfail" -ne 0 ] || _sadds="$_sadds
$_sadd"
      fi
      if [ "$_sfail" -eq 0 ]; then
        _sadd=$(_gate_drop_carried "$_smb" "$_sadds") || _sfail=2
        _slist="$_slist
$_sadd"
      fi
    fi
  fi

  printf '%s\n' "$_slist" | awk 'NF && !seen[$0]++'
  return "$_sfail"
}

# The slug a spec directory names: its path under `.specs/`, with `_archive/` stripped. Never the
# last component, which for the slashed slug `12-feat/sub` (case 179) is `sub`. #316.
gate_spec_slug() {  # <spec dir, such as .specs/12-x or .specs/_archive/12-x>
  _ss=${1#.specs/}
  printf '%s\n' "${_ss#_archive/}"
}

# Of <dirs>, one per line, print those whose slug <tree> does not carry under `.specs/` or
# `.specs/_archive/`: the adds that are the branch's own (Q1). A tree git cannot read is a failure,
# never "carries none". #316, review round 1.
_gate_drop_carried() {  # <tree-ish> <spec dirs, one per line>
  while IFS= read -r _cd; do
    [ -n "$_cd" ] || continue
    _cs=$(gate_spec_slug "$_cd")
    _cn=$(git ls-tree --full-tree "$1" -- ".specs/$_cs/spec.md" ".specs/_archive/$_cs/spec.md" 2>/dev/null) || return 2
    [ -n "$_cn" ] || printf '%s\n' "$_cd"
  done <<EOF
$2
EOF
}

# Run a git command that prints NUL-separated paths, and print the spec directories among them.
#
# `-z` because without it git quotes any path holding a byte outside printable ASCII, and a quoted
# path names no directory. A shell variable cannot hold a NUL, so the bytes become newlines in the
# pipe, and the command's status travels as a last line of its own: a pipeline's status is its last
# command's, and a status line that never arrives is a failure like any other.
_gate_spec_adds() {  # <command and arguments...>
  _ga=$( { "$@" 2>/dev/null; printf '\n_gate_status=%s\n' "$?"; } | tr '\0' '\n') || return 2
  [ "${_ga##*
}" = _gate_status=0 ] || return 2
  printf '%s\n' "$_ga" | awk '/^\.specs\/.+\/spec\.md$/ { sub(/\/spec\.md$/, ""); print }' || return 2
}

# Read a file from the working tree, or from a branch's own tree when <ref> is given.
#
# Absence returns 1 and unreadability returns 2, so the two stay distinguishable: the gate
# says different things about a receipt nobody wrote and a receipt it could not open, and
# collapsing them would make "I could not check" indistinguishable from "I checked".
_gate_read() {  # <ref, empty for the working tree> <path>
  if [ -z "$1" ]; then
    [ -f "$2" ] || return 1
    [ -r "$2" ] || return 2
    cat -- "$2"
  else
    # The tree's answer first and the object's second, so that 1 stays what it is above: a
    # tree that was read and does not name the path. Everything git could not read is a 2,
    # whether that is the tree or the blob the tree names — and so is any status that is not
    # the reader's own, because gate_spec_review_state reads whatever is neither 1 nor 2 as a
    # file it read. Case 200.
    gate_tree_names "$1" "$2"; _grc=$?
    case "$_grc" in 0) : ;; 1) return 1 ;; *) return 2 ;; esac
    # Named and unreadable is an object this repository does not have. The working-tree branch
    # above distinguishes that, and this one used to flatten it into "empty file" — and an
    # empty spec counts zero tasks, which is silence.
    git show "$1:$2" 2>/dev/null || return 2
  fi
}

# THE question this harness enforces: does this spec hold finished work with no usable review?
#
# One definition, three callers — `review-gate.sh` asks it about the branch you are standing
# on and about every other branch, and `check-unreviewed-work.sh` asks it about a pull
# request's head. Before #26 the receipt logic lived inline in the gate, so the only way to
# ask it anywhere else was to copy it, and a copy that can disagree with its subject is the
# defect class of #14 and #23.
#
# Prints a state, empty when there is nothing to demand. Callers compose their own messages,
# because a gate blocking your turn, a gate naming someone else's branch, and a CI step
# failing a pull request have to say different things about the same fact.
#
#   (empty)             no spec, no tasks authored, tasks still open, or reviewed and current
#   unreadable          the spec file is there and cannot be read
#   no-receipt          finished, and no receipt was ever written
#   receipt-unreadable  finished, and the receipt is there and cannot be read
#   verdict=<v>         finished, with a receipt that does not say CLEAN
#   unresolved-sha=<v>  finished and CLEAN, and <v> is absent or not a commit here
#   stale=<sha> <files> finished and CLEAN, but reviewable source moved since <sha>
gate_spec_review_state() {  # <spec dir> <tip sha> [<ref, empty for the working tree>]
  _dir=$1; _tip=$2; _ref=${3:-}

  _spec=$(_gate_read "$_ref" "$_dir/spec.md"); _rc=$?
  [ "$_rc" -eq 1 ] && return 0
  [ "$_rc" -eq 2 ] && { printf 'unreadable'; return 0; }

  [ "$(gate_total_tasks_text "$_spec")" -eq 0 ] 2>/dev/null && return 0
  [ "$(gate_open_tasks_text "$_spec")" -gt 0 ] 2>/dev/null && return 0

  _receipt=$(_gate_read "$_ref" "$_dir/.review-receipt"); _rc=$?
  [ "$_rc" -eq 1 ] && { printf 'no-receipt'; return 0; }
  [ "$_rc" -eq 2 ] && { printf 'receipt-unreadable'; return 0; }

  _verdict=$(printf '%s\n' "$_receipt" | sed -n 's/^verdict=//p' | head -1)
  [ "$_verdict" = CLEAN ] || { printf 'verdict=%s' "${_verdict:-missing}"; return 0; }

  _sha=$(printf '%s\n' "$_receipt" | sed -n 's/^reviewed_sha=//p' | head -1)
  [ "$_sha" = "$_tip" ] && return 0

  # A receipt whose sha this repository cannot resolve is worse than a stale one: nothing can
  # be compared, so returning "nothing changed" asserts a comparison that never happened.
  # Two shapes reach here, and the first is the sharper — `git diff ..<tip>` resolves an
  # omitted left side to HEAD, so a receipt recording no commit at all used to read as current
  # on the branch it was written on, and in CI compared two unrelated commits.
  #
  # This is the one new way to block, so its no-false-block argument is the line above: a
  # receipt written at the tip returns before ever reaching it. What does reach it is an
  # orphaned sha after a post-review rebase, which SHOULD block — the receipt describes
  # commits that no longer exist.
  if [ -z "$_sha" ] || ! git rev-parse --verify -q "$_sha^{commit}" >/dev/null 2>&1; then
    printf 'unresolved-sha=%s' "${_sha:-missing}"
    return 0
  fi

  # HEAD moved after the review. That is expected and fine when the trailing commits are the
  # work log and the spec's own Status flip. It is not fine when reviewable source moved,
  # because then the receipt describes code that no longer exists. Source globs come from
  # .steering/tech.md so this stays language-neutral.
  #
  # Two ways this used to fail OPEN, both the shell's doing rather than git's, and both
  # silent — which is the worst direction for a gate to fail in.
  #
  #   '*.py'   quotes inside a variable are not removed on expansion, so git received the
  #            literal pathspec '*.py' and matched nothing
  #   *.py     the shell expanded it against the repository root before git saw it, so a
  #            src/-layout project matched nothing and a flat one matched only top level
  #
  # Strip the quotes, then disable globbing across the word split so the pattern reaches git
  # intact. Word splitting is still wanted here: several globs are separated by spaces.
  _globs=$(gate_steering_value .steering/tech.md 'Source globs')
  [ -n "$_globs" ] || _globs='*'
  _globs=$(printf '%s' "$_globs" | tr -d "\"'")
  set -f
  # shellcheck disable=SC2086  # deliberate word-split: one :(glob) pathspec per argument (#1); quoted, case 160 goes red
  _changed=$(git diff --name-only "$_sha".."$_tip" -- $_globs 2>/dev/null)
  set +f
  [ -z "$_changed" ] && return 0
  printf 'stale=%s %s' "$_sha" "$(echo "$_changed" | tr '\n' ' ')"
}

# Has this branch's WORK reached the base — whatever merge style put it there?
#
# The skip beside this one asks `git merge-base --is-ancestor`, which answers whether a COMMIT
# was joined into the base's history. That is a different question, and the two coincide only
# under a merge commit or a fast-forward. A squash merge writes a new commit carrying the
# branch's result with no parent link back to it, so the tip is not an ancestor and never will
# be: the ancestry test is not failing intermittently, it is being asked something that can no
# longer be true. In a squash-merging repository the skip therefore never fired at all, and
# every shipped but undeleted spec branch stayed in the scan permanently. #182.
#
# Two steps, cheap first, and every unresolvable input leaves the skip unfired:
#
#   1. the base's tree carries this slug's spec, under .specs/ or .specs/_archive/
#   2. the branch holds nothing beyond what shipped
#
# Both locations count and neither alone does: `_archive/` is timely only after a sweep that
# `archive` runs on request, and `.specs/` is what that sweep empties.
#
# Step 1 alone is a fail-open, and it is the one this had to avoid — merge, then carry on
# committing to the same branch, and the slug is in the base while the branch holds work nobody
# reviewed. A slug reaching the base is a fact about the SPEC, not about the branch, and
# reading the first as the second is #26's defect returning through the door built to close
# its side effects. Case 134.
#
# Step 2's anchor is the FIRST commit on the base carrying the slug — the squash commit, since
# a spec is its branch's first commit and reaches the base only when the branch does. First
# rather than last, so `archive`'s later `git mv` into `_archive/` cannot drag the anchor
# forward onto work the branch never had. The comparison is scoped to the branch's OWN
# footprint rather than to all of `- Source globs:`, and that scoping is what makes it survive
# a base that moves: the anchor carries the branch's content at exactly those paths, while
# whatever else landed between the branch's fork and its squash is at other paths. Compared
# against the base's tip instead, the skip would stop firing the moment anyone touched one of
# those files again — the same permanent block wearing a new mechanism.
#
# The intersection is done in awk rather than by handing the footprint back to git as
# pathspecs. Word-splitting a path list splits a path containing a space into two pathspecs
# that match nothing, and a pathspec matching nothing makes `git diff` print nothing, which
# reads here as "shipped". That is a fail-open produced by quoting, which is #1's whole family.
gate_work_reached_base() {  # <slug> <tip sha> <base sha>
  _wslug=$1; _wtip=$2; _wbase=$3
  [ -n "$_wslug" ] && [ -n "$_wtip" ] && [ -n "$_wbase" ] || return 1

  _wlive=".specs/$_wslug/spec.md"
  _warch=".specs/_archive/$_wslug/spec.md"
  git cat-file -e "$_wbase:$_wlive" 2>/dev/null \
    || git cat-file -e "$_wbase:$_warch" 2>/dev/null \
    || return 1

  _wanchor=$(git rev-list --reverse "$_wbase" -- "$_wlive" "$_warch" 2>/dev/null | head -1)
  [ -n "$_wanchor" ] || return 1

  _wfork=$(git merge-base "$_wbase" "$_wtip" 2>/dev/null) || return 1
  [ -n "$_wfork" ] || return 1

  _wglobs=$(gate_steering_value .steering/tech.md 'Source globs')
  [ -n "$_wglobs" ] || _wglobs='*'
  _wglobs=$(printf '%s' "$_wglobs" | tr -d "\"'")

  # Exit status, never emptiness. `- Source globs:` is consumer-authored and nothing validates it —
  # `check-steering-anchors.sh` says in its own header that it judges only whether a value can be
  # honoured by the hook that reads it, and for this line that is whether the reader sees it at all,
  # never whether git accepts it — so a pathspec git rejects (`:(globs)` for `:(glob)`, a typo
  # echoing the key's own name) makes this exit 128 having printed nothing. Nothing is also what a
  # branch with no footprint prints, and reading the two as one silenced the gate on both call sites
  # with no diagnostic anywhere. Review round 1's BLOCKER, case 140. A git that could not answer
  # leaves the skip unfired, which is the same direction as every other guard here.
  # What did this branch touch? Two readings, and they are COMPLEMENTS rather than rivals —
  # each is blind to a shape the other catches, and "absent from the footprint" is read below
  # as "nothing to review", so a blind spot here is a silenced gate.
  #
  #   git log   the branch's own commits. Sees a path changed and then changed back — add a
  #             file, ship it, delete it on the branch — which a tree comparison cannot,
  #             because fork and tip agree at a path neither of them has. Round 3, case 142.
  #             Blind to a merge commit, for which --name-only prints no diff at all.
  #   git diff  the net tree comparison. Sees content that exists ONLY in a merge commit — a
  #             conflict fixup, or a hand edit between `git merge --no-commit` and the commit
  #             — because it does not care how the trees came to differ. Round 4, case 143.
  #
  # So: the union. It can only grow, and a larger footprint intersects more below, so the skip
  # fires LESS — widening is the safe way to be wrong here. Neither term widens the scoping the
  # design turns on, because _wfork is the merge base: whatever the base carried before this
  # branch forked is common to both sides and appears in neither term.
  set -f
  # shellcheck disable=SC2086  # deliberate word-split: one :(glob) pathspec per argument (#1); quoted, case 162 goes red
  _wlog=$(git log --format= --name-only "$_wfork".."$_wtip" -- $_wglobs 2>/dev/null) || { set +f; return 1; }
  # shellcheck disable=SC2086  # deliberate word-split: one :(glob) pathspec per argument (#1); quoted, case 163 goes red
  _wnet=$(git diff --name-only "$_wfork" "$_wtip" -- $_wglobs 2>/dev/null) || { set +f; return 1; }
  set +f

  # Folded here rather than piped above, for two reasons. A pipeline's status is its LAST
  # command's, so `git log ... | sort -u` hands back sort's success and undoes the exit-status
  # reads two lines up — case 140 went red on exactly that regression. And `git log
  # --name-only` separates each commit's paths with a BLANK line, which is the sentinel the
  # intersection below splits its two lists on; left in, the first commit boundary would be
  # read as the end of the footprint.
  #
  # `|| return 1` for the same reason every other step here has it, and it was missing for one
  # round: an awk that exits non-zero prints nothing, and nothing is what a branch with no
  # footprint prints — so the empty-footprint return below read "awk could not tell me" as
  # "the branch touched nothing". UNPINNED, and said out loud rather than implied: nothing
  # consumer-authored controls what awk DOES here — the program and its arguments are ours,
  # and only path names flow through as data — so the trigger is awk itself failing rather
  # than anything a project could write, and no cheap fixture produces that. This is the
  # difference from the rejected pathspec above, where the consumer authors the argument. The
  # anchor diff's guard is unpinned for its own reason, which case 140 records.
  #
  # `NF` and not `length($0)`: it is what guarantees _wfoot holds no blank-equivalent line,
  # which is what makes the sentinel below safe. The cost is a corner — a path named entirely
  # of spaces is dropped from the footprint, which narrows it, in the one place this function
  # argues that only widening is safe. Fixing it means giving the two lists a separator git
  # cannot emit; changing NF alone reintroduces case 139's truncation.
  _wfoot=$(printf '%s\n%s\n' "$_wlog" "$_wnet" | awk 'NF && !seen[$0]++') || return 1

  # Answered, and the answer is that the branch carries no reviewable source of its own. Step 1
  # already established the work is in the base. Distinct from the line above on purpose: "git
  # could not tell me" and "git told me nothing changed" must not collapse into one return.
  [ -n "$_wfoot" ] || return 0

  set -f
  # shellcheck disable=SC2086  # deliberate word-split: one :(glob) pathspec per argument (#1); quoted, case 161 goes red
  _wnow=$(git diff --name-only "$_wanchor" "$_wtip" -- $_wglobs 2>/dev/null) || { set +f; return 1; }
  set +f

  # Both lists go in on STDIN, separated by a blank line, because `awk -v foot="$list"` cannot
  # carry one: a -v assignment takes no newline, and BSD awk warns `newline in string` and
  # truncates at the first path. Truncated, the intersection sees one file and a branch that
  # carried on in any other reads as shipped — a fail-open produced by quoting, which is #1's
  # family, and the warning lands on the stderr a Stop hook hands to the user. A blank line is
  # a safe separator because `git diff --name-only` never emits an empty path. Case 139.
  # `|| return 1` for the same reason the two git calls above have it, and it was missing here
  # for two rounds: an awk that exits non-zero prints nothing, and nothing is what an empty
  # intersection prints. `$(a | b)` carries b's status in POSIX sh, so this is one token.
  _wleft=$(printf '%s\n\n%s\n' "$_wfoot" "$_wnow" | awk '
    !split_seen && NF == 0 { split_seen = 1; next }
    !split_seen { foot[$0] = 1; next }
    NF > 0 && $0 in foot { print }
  ') || return 1
  [ -z "$_wleft" ]
}

# One state, one sentence — for callers naming a branch that is not the one in hand, where
# the tailored second person of the gate's own messages would be wrong.
#
# Such a branch is read from its own tree, where "cannot be read" is never a file mode: it is
# an object git could not get. Until #191 the reader took that for a file that was not there,
# so the two unreadable sentences were all but unreachable and said only that the file existed.
# They name the cause now, because someone reading them in a partial clone with no network has
# nothing to repair and needs to be told so.
gate_review_state_sentence() {  # <state from gate_spec_review_state>
  _rwhy='from its own tree, because git cannot get an object that tree needs: a partial clone that cannot reach its remote, or a damaged object store'
  case "$1" in
    unreadable)         printf 'its spec cannot be read %s' "$_rwhy" ;;
    no-receipt)         printf 'every task is ticked and no reviewer receipt exists' ;;
    receipt-unreadable) printf 'its receipt cannot be read %s' "$_rwhy" ;;
    verdict=*)          printf "the recorded review verdict is '%s', not CLEAN" "${1#verdict=}" ;;
    unresolved-sha=*)   printf "its receipt records reviewed_sha '%s', which cannot be resolved here" "${1#unresolved-sha=}" ;;
    stale=*)            _r=${1#stale=}; printf 'source changed since the review at %s: %s' "${_r%% *}" "${_r#* }" ;;
    *)                  printf 'it holds finished work with no usable review' ;;
  esac
}
