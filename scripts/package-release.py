#!/usr/bin/env python3
"""Package the runtime distribution artifact for gate-sdd.

Bundles strictly the runtime payload into a standalone zip archive (dist/gate-sdd.zip):
  - plugin.json
  - .claude-plugin/ (plugin.json, marketplace.json)
  - skills/
  - agents/
  - hooks/
  - rules/ (rules/AGENTS.md)
  - assets/
  - AGENTS.md
  - README.md, README.ja.md, LICENSE

Strictly excludes repository-internal development assets:
  - .specs/, .steering/, .work_logs/, scripts/, evals/, docs/, .github/, .vscode/, .git*

Preserves Unix permissions (executable bits on hook scripts) and symbolic links.
Fails closed (exit 1) if any required runtime component is missing.
"""

import argparse
import os
import pathlib
import stat
import sys
import time
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent

REQUIRED_COMPONENTS = [
    "plugin.json",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    "skills",
    "agents",
    "hooks",
    "rules/AGENTS.md",
    "assets",
    "AGENTS.md",
    "README.md",
    "LICENSE",
]

# Additional optional documentation files to bundle if present
OPTIONAL_FILES = [
    "README.ja.md",
]

EXCLUDED_NAMES = {
    "__pycache__",
    ".DS_Store",
}

EXCLUDED_EXTENSIONS = {
    ".pyc",
    ".pyo",
}


def add_to_zip(zf: zipfile.ZipFile, base_dir: pathlib.Path, rel_path: str) -> None:
    full_path = base_dir / rel_path

    # Check for symlink first
    if os.path.islink(full_path):
        target = os.readlink(full_path)
        info = zipfile.ZipInfo(rel_path)
        info.create_system = 3  # Unix
        lstat = os.lstat(full_path)
        info.date_time = time.gmtime(lstat.st_mtime)[:6]
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        zf.writestr(info, target)
        return

    if full_path.is_dir():
        # Add directory entry
        dir_arc = rel_path.rstrip("/") + "/"
        info = zipfile.ZipInfo(dir_arc)
        info.create_system = 3
        st = full_path.stat()
        info.date_time = time.gmtime(st.st_mtime)[:6]
        info.external_attr = (stat.S_IFDIR | (st.st_mode & 0o777)) << 16
        zf.writestr(info, b"")

        for child in sorted(full_path.iterdir()):
            if child.name in EXCLUDED_NAMES or child.suffix in EXCLUDED_EXTENSIONS:
                continue
            child_rel = f"{rel_path.rstrip('/')}/{child.name}"
            add_to_zip(zf, base_dir, child_rel)
    else:
        # Regular file
        info = zipfile.ZipInfo(rel_path)
        info.create_system = 3
        st = full_path.stat()
        info.date_time = time.gmtime(st.st_mtime)[:6]
        info.external_attr = (stat.S_IFREG | (st.st_mode & 0o777)) << 16
        with open(full_path, "rb") as f:
            zf.writestr(info, f.read(), compress_type=zipfile.ZIP_DEFLATED)


def package_release(source_dir: pathlib.Path, output_zip: pathlib.Path) -> None:
    # 1. Verify all required components exist
    for rel in REQUIRED_COMPONENTS:
        p = source_dir / rel
        if not (p.is_file() or p.is_dir() or p.is_symlink()):
            print(f"package-release: missing required runtime component: {rel}", file=sys.stderr)
            sys.exit(1)

    # 2. Collect top-level payload entries
    payload_entries = [
        "plugin.json",
        ".claude-plugin",
        "skills",
        "agents",
        "hooks",
        "rules",
        "assets",
        "AGENTS.md",
        "README.md",
        "LICENSE",
    ]
    for opt in OPTIONAL_FILES:
        if (source_dir / opt).exists():
            payload_entries.append(opt)

    # 3. Create destination directory if needed
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    # 4. Build zip archive
    temp_zip = output_zip.with_suffix(".tmp.zip")
    try:
        with zipfile.ZipFile(temp_zip, "w") as zf:
            for entry in payload_entries:
                entry_path = source_dir / entry
                if not (entry_path.exists() or entry_path.is_symlink()):
                    continue
                add_to_zip(zf, source_dir, entry)
        if output_zip.exists():
            output_zip.unlink()
        temp_zip.rename(output_zip)
    except Exception as e:
        if temp_zip.exists():
            temp_zip.unlink()
        print(f"package-release: failed to package release: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"package-release: packaged runtime payload to {output_zip}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Package gate-sdd runtime distribution artifact")
    parser.add_argument("output", nargs="?", default="dist/gate-sdd.zip", help="Destination zip path")
    parser.add_argument("--source", default=None, help="Source repository root (default: repo root)")
    args = parser.parse_args()

    source = pathlib.Path(args.source).resolve() if args.source else ROOT
    output = pathlib.Path(args.output)
    if not output.is_absolute():
        output = (ROOT / output).resolve()

    package_release(source, output)


if __name__ == "__main__":
    main()
