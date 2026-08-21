---
name: worklog
description: Append a dated entry to .work_logs/ summarizing what changed this session — activities, decisions, next steps. Use at the end of a working session or right after implement.
---

# worklog — Record the session

A spec says what was intended. A diff says what changed. Neither says **why the approach shifted at 3pm**, and that is the thing a future session — or a colleague — most needs and can least reconstruct.

## Steps

1. Determine today's date. The target file is `.work_logs/<YYYY-MM-DD>.md`; create it if missing.
2. Gather facts rather than impressions: commits since the last entry, files changed, specs touched, decisions made, threads left open.
3. Append an entry from the template. Attribute it to whoever is running this.
4. Keep it skimmable. Bullets, not prose.

## Entry template

```markdown
## <YYYY-MM-DD> — <contributor>

### Summary
<1–2 lines: what moved>

### Activities
- <spec slug> (<issue>): <what happened, including Red/Green/Refactor progress>

### Decisions
- <decision> — <why, and what it rules out>

### Next steps
- [ ] <the specific next action, not "continue">
```

## Rules

- **Append. Never rewrite past entries.** This is an audit trail; a corrected past is not one. If an earlier entry was wrong, say so in today's entry.
- One section per session. Several people on the same day means several sections under that date, not a merged one.
- **Record decisions with their reasons**, including the options rejected. A decision without its "why" gets re-litigated in three weeks by someone who has forgotten there was a reason.
- Reference specs by slug and issues by number so entries cross-link to `.specs/` and the tracker.
- If the reviewer produced findings that were accepted rather than fixed, they belong in Decisions with the reason. Silent deferral is how a Medium becomes a Blocker later.
