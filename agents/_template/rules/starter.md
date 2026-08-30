# Rulebook: {{TOPIC}} — `{{PREFIX}}-*`

Scope: {{SCOPE}}. Load when the diff touches {{WHEN}}.

The project's formatter and linter enforce the mechanical subset of this. **Do not report what they catch.** These rules exist for what a formatter and a type checker cannot see: intent, contract shape, missing tests, and logic that is valid but wrong.

Sources are pinned in `../rules-lock.json`.

---

## {{PREFIX}}-001 — <one-line rule, stated as the property that must hold>
**Severity: <BLOCKER|HIGH|MEDIUM|LOW>**

<Why this matters here, in two or three lines. Name the failure it prevents, not the style it enforces — a rule whose rationale is "it looks better" will lose every argument it is ever in.>

Check: <what to look for in a diff, concretely enough that two reviewers would flag the same lines.>

---

<!-- Writing rules that survive contact with real diffs:

- One property per rule, with an id that can be cited in a commit message.
- Severity is anchored to the quality property this project owns, not to taste.
- If the linter already catches it, delete the rule. Duplicated enforcement produces double findings and teaches people to skim the report.
- Prefer rules with an observable check. "Be careful with concurrency" is not a rule; "shared mutable state across tasks names its lock, queue, or immutability" is.
- Six to ten rules per file. A rulebook nobody finishes is a rulebook nobody applies. -->
