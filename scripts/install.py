#!/usr/bin/env python3
"""Copy one skill into a selected host directory without overwriting existing skills."""
import argparse
import os
from pathlib import Path
import re
import shutil


def install(source, destination):
    source = Path(source).resolve()
    destination = Path(destination).expanduser().resolve()
    text = (source / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"^name: ([a-z0-9-]+)\s*$", text, re.M)
    if not match or match[1] != source.name or len(match[1]) > 64:
        raise ValueError("Skill folder and frontmatter name must match")
    if destination == source or source in destination.parents:
        raise ValueError("Destination cannot be inside the source skill")
    if any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("Skill contains symbolic links; use a self-contained folder")
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / source.name
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", default=str(Path(__file__).resolve().parents[1] / "skills/expert-distiller"))
    parser.add_argument("--dest", default=str(Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills"))
    args = parser.parse_args()
    try:
        print(f"Installed: {install(args.source, args.dest)}")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Installation stopped: {exc}\n")


if __name__ == "__main__":
    main()
