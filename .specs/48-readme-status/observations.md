# Observations — #48

## T1 — the greps, red

- `v0\.2\.3`: 2 hit(s)
- `never been executed`: 1 hit(s)
- `no reviewer has yet`: 1 hit(s)
- `2\.1\.238`: 4 hit(s)
- `すべての diff`: 1 hit(s)
- `verified.md, fidelity.md, skill-anatomy.md, layout.md$`: 1 hit(s)

- `README.md` 7bb1395ea4f8
- `README.ja.md` 9e59e36abed1
- `docs/layout.md` dac8738b1dcf
- `docs/verified.md` 282e993f1481

## T2 — the rewrite

Both Status sections rewritten as mirrors; the matrix line in both READMEs and in `verified.md`'s table per clarification 1; `layout.md`'s `docs/` line; the eval sentence stating the exit-0 no-op. Every T1 grep returns nothing; `2.1.238` survives only in the dated note in `verified.md`'s table. Validators run after the last write with a loop that stops on the first failure — below.
