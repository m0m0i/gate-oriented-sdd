# Baseline — captured before the first inception skill ran

Task T1 of `.specs/55-run-northstar-prd-epics/spec.md`. Every value here is the before-side of AC1, AC2 and AC8. Re-verified in T6.

- Captured: 2026-08-29T12:07:48Z
- HEAD: a6f8ca933a036e65a943750ecf457ab2a7478511
- Branch: 55-run-northstar-prd-epics

## Validators (the eight on `.steering/tech.md`'s `- Validators:` line)

| Command | Exit | Last line |
| :-- | :-- | :-- |
| `./scripts/check-leakage.sh` | 0 | check-leakage: clean |
| `./scripts/check-manifests.py` | 0 | check-manifests: both manifests agree |
| `./scripts/check-receipt-schema.py` | 0 | check-receipt-schema: 7 field(s) agree across 3 copies |
| `./scripts/check-skill-contracts.py` | 0 | check-skill-contracts: 9 skill contract(s) present |
| `./scripts/check-templates.py` | 0 | check-templates: 10 task line(s) across 3 template(s), no split red steps |
| `./assets/check-steering-anchors.sh` | 0 | check-steering-anchors: 5 of 5 anchor(s) resolved, none unreadable |
| `./assets/check-locks.py` | 0 | check-locks: 6 pinned file(s) match their locks in .claude/agents, agents |
| `./scripts/test-gates.sh` | 0 | test-gates: 52 passed, 0 failed |

## The line that must not change

```
6:- Owns: gates never fail open
```

- sha256 of that line: 3f52ee31c24c7a0c53ad418b7e72988d7e077a131c57419dfa4d69dc622fc1cc

## Files that must be byte-identical afterwards

```
d72253ff0a95f6a45eed0fa375a237d4140dde2b866c93f78e797235899ad855  docs/BACKLOG.md
635a65f27269ca7c5f647ef85bc0d7dbba35c0f692cf1f4fe13e7368bd644260  .steering/product.md
5e5440558ecda675e4a3f849ba5154c495c89d12ca6e45124d428aa19e0f6a77  .steering/tech.md
061e0ff74ddbdf90b50bce3dd9ba1d48a8e9c2087156b67368132737b8daeaea  .steering/structure.md
```

## Documents absent at baseline

- absent: `docs/NORTH_STAR.md`
- absent: `docs/PRD.md`
- absent: `docs/EPICS.md`
- absent: `docs/CONTRACT.md`
- absent: `docs/DESIGN.md`
- absent: `docs/decisions`

## Probe P2 — the `LV-` prefix is unused at baseline

```
$ grep -rl 'LV-' --include='*.md' --include='*.py' --include='*.sh' . \
    | grep -v '55-run-northstar-prd-epics'
(no matches)
```

Outside this spec's own directory: **0 matches.** The two files that do contain `LV-` are `spec.md` and this file, both of which name the prefix while describing the probe.

So any `LV-` appearing in `docs/PRD.md` or `docs/EPICS.md` after the run came from `northstar`, not from the repository. That is AC6's mechanism.

*Recorded correction:* the first version of this section ran the filter as `^\./\.specs/55-`, which matched nothing because `grep -rl` emitted paths without the `./` prefix — so it printed its own two files directly beneath a sentence claiming no matches. Caught and fixed before the first skill ran. Noted here rather than silently overwritten, because a baseline whose corrections are invisible is not a baseline.
