#!/bin/sh
# plugin-gate.sh — the gates as the plugin runs them on Claude Code (#256).
#
# .claude-plugin/hooks.json runs `sh "${CLAUDE_PLUGIN_ROOT}/hooks/plugin-gate.sh" <gate>` on
# Stop and SessionStart, so a fix to a gate reaches a project by plugin update rather than by
# re-running `init` and opening a pull request in every repository that copied it. The gate
# itself is unchanged and runs beside this file, with the project as cwd (verified: V1 in
# docs/verified.md). What this wrapper adds is the three decisions a plugin-shipped gate has to
# make that a copied one never did, and on SessionStart one statement a copy never needed to
# make: where the plugin is, for the session's own shell — (0) below.
#
#   1. A project without .steering/ does not use the harness. A user-scope install reaches
#      every project on the machine, so the gate must be silent there — exit 0, no output.
#   2. A project that still runs its own copy of the same gate, from its .claude/settings.json,
#      would run the gate twice: Claude Code runs the plugin's hook AND the project's for the
#      same event (V2). So this stands down — but only on EVIDENCE that the copy runs, and
#      that takes both halves: the settings this launch read name the gate's file under the
#      gate's event, AND the file the entry names is on disk where the entry's own shell
#      would find it — by a relative or absolute path, or through $CLAUDE_PROJECT_DIR (#262).
#      An entry that reaches the copy any other way is not evidence, and both gates run. The
#      copied file alone is not evidence; a project with the file and no entry runs this gate.
#      The entry alone is not evidence either: the entry every pre-0.23.0 project carries is
#      `[ -f .claude/hooks/quality-gate.sh ] || exit 0; sh .claude/hooks/quality-gate.sh`,
#      which exits 0 by itself once the copy is gone, so an interrupted migration (scripts
#      deleted, entries not yet) had the project's entry silent and this wrapper standing
#      down on it (review round 2). Neither running is the
#      fail-open under `- Owns: gates never fail open`; both running costs a second validator
#      pass. The two mistakes are not symmetric, so the test is biased toward running.
#   3. A gate missing from the plugin is a broken install, and a broken install is loud. The
#      shape is the gates' own bootstrap guard: JSON on stdout for Antigravity, the sentence on
#      stderr for Claude Code, exit 2.
#
# A POSIX hook cannot parse JSON by event, so the evidence in (2) is text, and the text is
# held to two shapes rather than two words: the gate's filename on a `"command"` line, and the
# event as a KEY (`"Stop":`). The first draft asked only whether the file mentioned each
# anywhere, and Claude Code itself produces the counter-example: approving a by-hand run of
# the gate with "don't ask again" writes `"permissions": {"allow": ["Bash(sh
# .claude/hooks/quality-gate.sh:*)"]}` into settings.local.json, and a Stop hook for a
# notification is the documented example — together they read as the gate running under
# Stop, and the plugin's gate stood down for nothing (review round 1). What remains is a
# settings file with a `"command"` naming an existing copy of the gate and a `"Stop":` key
# that does not run it, which nothing writes. Antigravity never runs this file; its gates
# are copied by `init`, because a plugin hook there runs with the plugin directory as cwd
# (hooks/templates/README.md).
set -u

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
gate=${1:-}

_plugin_gate_block() {  # the bootstrap guard's shape; nothing interpolated is user-authored
  printf '{"decision":"continue","reason":"%s"}\n' "$1"
  printf '%s\n' "$1" >&2
  exit 2
}

# The gate decides the event, and the name is a closed list: a path from outside the plugin's
# hooks/ is not a gate this wrapper runs, whatever it is called.
case "$gate" in
  quality-gate.sh|review-gate.sh) event=Stop ;;
  steering-digest.sh) event=SessionStart ;;
  *) _plugin_gate_block "Plugin gate: '$gate' is not a gate this wrapper runs (quality-gate.sh, review-gate.sh or steering-digest.sh). The plugin's .claude-plugin/hooks.json names the wrong thing, so re-install the plugin rather than treating this turn as a pass." ;;
esac

gate_re=$(printf '%s' "$gate" | sed 's/\./\\./g')   # the name as a pattern: its dots literal

# (0) Tell the session's own shell where the plugin is (#264). CLAUDE_PLUGIN_ROOT reaches this
# hook and, by Claude Code's documentation, never a command the agent runs through its Bash
# tool — so the two checks `init` copies into a project, which find gate-lib.sh through the
# plugin since #256, passed at turn end and failed when `implement` or a reviewer ran them.
# On SessionStart Claude Code hands each hook a CLAUDE_ENV_FILE that it sources before every
# Bash command of the session, a subagent's included (verified: docs/verified.md), and the
# checks read GATE_SDD_PLUGIN_ROOT last, after any copy. Written before (1) and (2), because
# both sessions that need it most are ones this wrapper would otherwise leave: `init` writes
# .steering/ in a session that started without it, and a migration runs in one whose digest
# stood down; step 4 of `init` runs the validators by hand in both. Elsewhere the variable is
# inert. The file is shared with other hooks and kept across --resume and /compact, gaining a
# line per SessionStart, so the export is appended only when the last one there differs, never
# joined to a line another hook left unterminated, and never written for a root holding a
# newline, which would split it. A failed write is silent — SessionStart has no blocking
# channel — and lands where it is loud anyway: the check's own error, naming what to set.
# Silent means the group's redirect: the shell reports a failed `>>` before a 2>/dev/null on
# the same command applies (#262).
if [ "$event" = SessionStart ] && [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  _root=${DIR%/*}
  case "$_root" in
    *'
'*) ;;
    *)
      _line="export GATE_SDD_PLUGIN_ROOT='$(printf '%s' "$_root" | sed "s/'/'\\\\''/g")'"
      if [ "$(grep '^export GATE_SDD_PLUGIN_ROOT=' "$CLAUDE_ENV_FILE" 2>/dev/null | tail -n 1)" != "$_line" ]; then
        _nl=""
        [ -s "$CLAUDE_ENV_FILE" ] && [ -n "$(tail -c 1 "$CLAUDE_ENV_FILE")" ] && _nl='
'
        { printf '%s%s\n' "$_nl" "$_line" >> "$CLAUDE_ENV_FILE"; } 2>/dev/null || :
      fi
      ;;
  esac
fi

# Anchor to the repository root, as the gates do, so .steering/ and .claude/ resolve from
# wherever the hook was invoked. Where it was invoked is kept first: it is the directory the
# project's own hooks run in, so (2) resolves an entry's relative path from it (#262).
_start=$(pwd)
if repo_root=$(git rev-parse --show-toplevel 2>/dev/null); then
  cd "$repo_root"
fi

# (1) Not a harness project: silent.
[ -d .steering ] || exit 0

# (2) The project runs its own copy of this gate under this event: stand down. Expansion is
# off across the block, so a word holding `*`, `?` or `[` is tested as written rather than as
# whatever it matches here, which is not what the entry's own quotes would run (#262).
#
# CLAUDE_PROJECT_DIR is the one variable an entry's path is resolved through. Claude Code's hooks
# documentation asks for it in a command, each placeholder in double quotes, and the plugin's
# hook and the project's were measured seeing one value (docs/verified.md, #262). Unquoted, the
# entry's own shell splits and expands the value, so an unquoted spelling counts only where the
# value holds no space, tab, newline, `*`, `?` or `[`: elsewhere the entry runs nothing, and
# standing down on it would leave no gate at all.
#
# The settings read are the ones this launch read. Launched below the git root, Claude Code
# reads the launch directory's settings.json and settings.local.json and the root's
# settings.local.json, NOT the root's settings.json, and runs every hook with the launch
# directory as cwd and as CLAUDE_PROJECT_DIR (measured, docs/verified.md). Reading the root's
# two files, as this did until #262, stood down on a root entry that never ran: with the plugin
# enabled at user scope, no gate at all. Launched at the root, the local file is read twice,
# for one grep. That root is CLAUDE_PROJECT_DIR's, found with `git -C`, not the one this script
# anchored to: the hook can start in another working tree the Bash tool cd'ed into (P1, P4), and
# its local file is not one the launch read (#262, review round 1). Without CLAUDE_PROJECT_DIR —
# outside Claude Code — the root's two files.
_pd=${CLAUDE_PROJECT_DIR:-}
case "$_pd" in
  *' '*|*'	'*|*'
'*|*'*'*|*'?'*|*'['*) _pd_plain= ;;
  *) _pd_plain=1 ;;
esac
if [ -n "$_pd" ]; then
  _pd_root=$(git -C "$_pd" rev-parse --show-toplevel 2>/dev/null) || _pd_root=$_pd
  set -- "$_pd/.claude/settings.json" "$_pd/.claude/settings.local.json" "$_pd_root/.claude/settings.local.json"
else
  set -- .claude/settings.json .claude/settings.local.json
fi
set -f
for f in "$@"; do
  [ -f "$f" ] || continue
  # Line layout is not assumed: a minified settings file is one line, and a line-wise test
  # read its permissions entry as its Stop command. The gate's name must sit INSIDE a
  # "command" string value — from the opening quote to the name with no unescaped quote
  # between — and the event must be a key.
  if grep -qE -- "\"command\"[[:space:]]*:[[:space:]]*\"([^\"\\\\]|\\\\.)*$gate_re" "$f" 2>/dev/null \
     && grep -qE -- "\"$event\"[[:space:]]*:" "$f" 2>/dev/null; then
    # The entry is evidence only with the file it names on disk. Every path-shaped word
    # whose last component is the gate's name is tried; one that exists is the copy that
    # runs. Ending in the name is not enough: a project's own `code-review-gate.sh` is not
    # review-gate.sh (#256 round 3). A word runs to a space or a quote, but a JSON-escaped
    # quote (`\"`) is part of it: until #262 it ended the word, and the documented
    # `\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/<gate>` was tested as `/.claude/hooks/<gate>`, at
    # the filesystem root. The escaped quotes are dropped once a word is read; one leading the
    # word is what makes the variable quoted. A path reached through any other variable does
    # not resolve here and does not stand this gate down, which is the noisy direction, on
    # purpose: a wrapper's guess at a variable the entry may set itself is how a gate goes quiet.
    #
    # The one character before a word is kept when it is a single quote or a backslash, after
    # which the entry's shell expands nothing. A lone backslash escapes what follows, so its
    # word is skipped. A single-quoted word counts only as a plain path: one holding a `$` or a
    # backslash is skipped, since `sh '$CLAUDE_PROJECT_DIR/…'` runs a file named for the
    # variable, which is no file at all. Until review round 1 the quote ended the word there,
    # the word read as unquoted, and this stood down while no gate ran.
    for _w in $(grep -oE -- "[\\\\']?([^\"' \\\\]|\\\\\")*$gate_re" "$f" 2>/dev/null); do
      case "$_w" in
        '\"'*) ;;
        '\'*|"'"*'$'*|"'"*'\'*) continue ;;
        "'"*) _w=${_w#"'"} ;;
      esac
      _path=$(printf '%s' "$_w" | sed 's/\\"//g')
      case "$_path" in
        '$CLAUDE_PROJECT_DIR/'*|'${CLAUDE_PROJECT_DIR}/'*|'${CLAUDE_PROJECT_DIR:-.}/'*)
          [ -n "$_pd" ] || continue
          case "$_w" in '\"'*) ;; *) [ -n "$_pd_plain" ] || continue ;; esac
          _path=${_path#*/}
          case "$_path" in *'$'*) continue ;; esac
          _path="$_pd/$_path" ;;
        *'$'*) continue ;;
        /*) ;;
        *) _path="${_start:-.}/$_path" ;;
      esac
      case "$_path" in "$gate"|*/"$gate") [ -f "$_path" ] && exit 0 ;; esac
    done
  fi
done
set +f

# (3) The gate runs from here, beside this file, with the project as cwd.
[ -f "$DIR/$gate" ] || _plugin_gate_block "Plugin gate: $gate is missing from the plugin's hooks/ directory beside plugin-gate.sh, so the gate cannot run. Re-install the plugin and run again rather than treating this turn as a pass."
exec sh "$DIR/$gate"
