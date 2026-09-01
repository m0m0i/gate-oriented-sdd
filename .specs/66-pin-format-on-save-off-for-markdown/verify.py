#!/usr/bin/env python3
"""AC1 and AC2: the workspace setting exists, parses, and says only what it should."""
import json, pathlib, re, sys

p = pathlib.Path(".vscode/settings.json")
fails = []
if not p.is_file():
    sys.exit("FAIL: .vscode/settings.json does not exist")

raw = p.read_text()
# Editors accept JSON-with-comments here. Strip line comments the way one does, then parse —
# so "it looks like JSON" is never mistaken for "it parses".
stripped = re.sub(r"^\s*//.*$", "", raw, flags=re.M)
try:
    data = json.loads(stripped)
except json.JSONDecodeError as e:
    sys.exit(f"FAIL: does not parse as JSONC: {e}")

if list(data) != ["[markdown]"]:
    fails.append(f"expected exactly one key '[markdown]', got {list(data)}")
md = data.get("[markdown]", {})
if list(md) != ["editor.formatOnSave"]:
    fails.append(f"expected exactly one key under [markdown], got {list(md)}")
if md.get("editor.formatOnSave") is not False:
    fails.append(f"editor.formatOnSave is {md.get('editor.formatOnSave')!r}, want False")

if fails:
    for f in fails: print(f"FAIL: {f}", file=sys.stderr)
    sys.exit(1)
print("AC1/AC2: .vscode/settings.json parses, and carries only [markdown].editor.formatOnSave = false")
