# Product — gate-oriented-sdd

A spec-driven development harness, packaged as one plugin directory that installs into both
Claude Code and Google Antigravity.

- **Owns: gates never fail open.**

That line is machine-read by the reviewer and the steering digest, and it is the anchor every
severity is judged against. A defect that lets a gate exit 0 when it should have blocked is at
least HIGH; one that makes a gate silently stop checking is a BLOCKER. The reason it is *this*
property and not, say, ergonomics: a gate that fails open is indistinguishable from a working one,
so it survives exactly as long as it takes to matter. Three of the first five bugs filed against
this repo were that shape (#1, #14, #16), which is evidence rather than intuition.

## Who uses it

Developers running an agent against their own codebase who want the review step to be a
mechanical gate rather than a request the model can decline. Secondarily, people reading it as a
reference implementation of hook-enforced process.

## What it deliberately is not

- **Not a document generator.** Every skill has to terminate in something the harness mechanically
  uses. A skill whose only output is a document a human might read is out of scope.
- **Not a supported product.** Pre-release, with a tested-against version matrix.
- **Not configurable in its directory names.** `.specs/`, `.steering/`, `.work_logs/` are literal in
  every skill body, which is what lets one copy of a skill serve every project without templating.
- **Not a language abstraction.** Three concrete reviewers people copy beat one abstraction people
  configure.

## The claim that has to stay true

The review gate is enforced by a hook, not requested by prose. Anything that turns an enforced gate
back into guidance has removed the reason this repo exists.
