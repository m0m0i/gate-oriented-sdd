---
name: contract
description: Write the development contract — the language, style, testing, and review rules this project holds itself to — and compile the enforceable ones into the reviewer's rulebook. Use at project inception, or when recurring review findings reveal an unwritten rule.
---

# contract — The rules this project holds itself to

A coding-standards document that only exists as prose is a document nobody re-reads. This skill writes one, then does the thing that makes it matter: **compiles every rule that can be enforced into the place that enforces it.**

Each rule lands in exactly one of three tiers, and the tier is chosen by *how the rule can be checked*, not by how important it feels:

| Tier | Destination | Enforced by |
| :-- | :-- | :-- |
| **Mechanical** | linter, formatter, type checker config | the quality gate — it cannot be skipped |
| **Judgment** | the reviewer's rulebook, as a rule with an id | the reviewer — it is cited in findings |
| **Narrative** | the contract document only | nothing; it is context, and it is honest about that |

A rule that lands in Narrative is not a lesser rule. It is a rule you have decided not to enforce, which is worth knowing.

## Where it goes

`<docs>/CONTRACT.md` — with its Judgment-tier rules compiled into the reviewer's rulebook.

`<docs>` is the `- Docs:` line in `.steering/tech.md`, which defaults to `docs/`. In a multi-repo product it points at the shared documentation repository instead, so product-level truth has one home rather than one per repo.

## Steps

1. **Read what the project already does**, before writing what it should. `.steering/tech.md`, the linter and formatter config, the existing code, and — most valuable — the last fifty commits and any review comments. A convention followed in the code and absent from the document is still a convention.
2. **Draft the rules** from the template below. Prefer rules the project already follows; a contract full of aspirations it has never met is a contract that gets ignored on day one.
3. **Tier every rule.** For each, ask: could a linter check this? Then it belongs in the linter, and writing it in prose instead is choosing not to enforce it. Could a reviewer check it against a diff? Then it belongs in the rulebook with an id. Neither? Narrative.
4. **Compile the Judgment tier into the rulebook.** Add each as a rule in the project's reviewer rulebook — id, severity, rationale, and a concrete check. Severity is anchored to the quality property from `.steering/product.md`. Then re-pin the lock.
5. **Move the Mechanical tier into config**, or say plainly that it is not enforced and why.
6. Record in `.steering/tech.md` where the contract lives and that the rulebook is generated from it.

## Template

```markdown
# Development contract

- Applies to: <what code this governs>
- Quality anchor: <the property from .steering/product.md that decides severities>

## Language and tooling
<language versions, package manager, and the one command each for build, test, lint>

## Style
<what the formatter owns — say "the formatter decides" rather than restating it>
<what it does not own: naming, file organisation, module boundaries>

## Testing
<what must be tested, what "done" means, what may not be mocked>

## Review
<what blocks a merge, what is advisory>

## Rules
| id | Rule | Tier | Severity | Enforced by |
| :-- | :-- | :-- | :-- | :-- |
| <PFX-001> | <the property that must hold> | Judgment | HIGH | rulebook |
| <PFX-002> | <...> | Mechanical | — | lint rule <code> |
| <PFX-003> | <...> | Narrative | — | nothing — context only |
```

## Rules

- **Rules the linter already enforces do not get written twice.** Duplicated enforcement produces double findings and teaches people to skim the report.
- **Every Judgment rule needs a concrete check** — something specific enough that two reviewers reading the same diff flag the same lines. "Be careful with X" is not a rule.
- **Justify by failure, not by taste.** State what goes wrong when the rule is violated. A rule whose rationale is "it reads better" loses every argument it is ever in.
- Prefer few rules that are enforced over many that are aspirational.
- Re-pin the rulebook lock after compiling; an unpinned edit means the reviewer is citing rules that were never reviewed.

## Red flags

Stop and reconsider if you catch yourself doing any of these:

- Writing a rule you cannot state a failure for. That is taste, and it belongs in a code review conversation, not a contract.
- Putting a lintable rule in Narrative because configuring the linter is more work. That is choosing not to enforce it while appearing to.
- Producing thirty rules on a first pass. A contract nobody finishes is a contract nobody applies; ten enforced rules beat thirty ignored ones.
- Copying a style guide wholesale. The rules that matter are the ones this project has actually argued about.
