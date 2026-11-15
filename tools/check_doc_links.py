#!/usr/bin/env python3
"""Markdown relative link and image link checker.

Scans Markdown (*.md) files in the repository (excluding .git and build dirs)
for broken relative links and images. Reports missing targets as:
    file:line -> target
Ignores external URLs (http/https/mailto) and pure in-page #anchors.
Exits 1 if any broken targets are found, 0 otherwise.
"""

import os
import re
import sys
import urllib.parse
from pathlib import Path

# Match Markdown links and image links: [text](target) and ![text](target).
# Handles nested brackets (e.g. [![alt](img.png)](link.html)),
# angle-bracket enclosed destinations (<path with spaces.md>),
# balanced parentheses in URLs, and optional link titles in quotes or parens.
LINK_PATTERN = re.compile(
    r'!?\[((?:[^\[\]]|\[(?:[^\[\]]|\[[^\]]*\])*\])*)\]\(\s*(?:<([^>]+)>|((?:[^\s\(\)]|\([^\s\(\)]*\))+))(?:\s+(?:"[^"]*"|\'[^\']*\'|\([^)]*\)))?\s*\)'
)


def is_excluded_dir(name: str) -> bool:
    """Check if a directory should be skipped (e.g. .git, build directories)."""
    lower = name.lower()
    if lower == ".git" or lower.startswith(".git"):
        return True
    if lower in ("build", "_build", ".build", ".cache", "__pycache__"):
        return True
    if lower.startswith("build-") or lower.startswith("build_") or lower.startswith("cmake-build-"):
        return True
    return False


def extract_links(line: str):
    """Extract link targets from a line of Markdown text."""
    links = []
    for m in LINK_PATTERN.finditer(line):
        inner_text = m.group(1)
        target = m.group(2) if m.group(2) is not None else m.group(3)
        # If inner_text contains nested links/images, extract them as well
        if "[" in inner_text and "](" in inner_text:
            links.extend(extract_links(inner_text))
        if target:
            links.append(target.strip())
    return links


def check_file(file_path: Path, repo_root: Path):
    """Check a single Markdown file for broken relative links."""
    broken = []
    rel_file = file_path.relative_to(repo_root).as_posix()
    in_code_block = False

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line_no, line in enumerate(f, 1):
                stripped = line.strip()
                if stripped.startswith("```") or stripped.startswith("~~~"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    continue

                links = extract_links(line)
                for target in links:
                    # Ignore pure anchors
                    if target.startswith("#"):
                        continue
                    # Ignore http(s) and mailto links
                    target_lower = target.lower()
                    if target_lower.startswith(("http://", "https://", "mailto:")):
                        continue

                    # Strip anchor fragment and query parameters for filesystem check
                    file_part = target.split("#", 1)[0].split("?", 1)[0]
                    clean_file = urllib.parse.unquote(file_part).strip()
                    if not clean_file:
                        continue

                    clean_file = clean_file.replace("\\", "/")

                    # Resolve target path
                    if clean_file.startswith("/"):
                        target_path = repo_root / clean_file.lstrip("/")
                    else:
                        target_path = file_path.parent / clean_file

                    if not target_path.exists():
                        broken.append((rel_file, line_no, target))
    except Exception as e:
        print(f"Error reading {rel_file}: {e}", file=sys.stderr)

    return broken


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0)

    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        root = Path(sys.argv[1]).resolve()
    else:
        root = Path(__file__).resolve().parent.parent

    if root.is_file():
        repo_root = root.parent
        broken = check_file(root, repo_root)
    else:
        repo_root = root
        broken = []
        for dirpath, dirnames, filenames in os.walk(repo_root):
            dirnames[:] = [d for d in dirnames if not is_excluded_dir(d)]
            for fname in filenames:
                if fname.lower().endswith(".md"):
                    file_path = Path(dirpath) / fname
                    broken.extend(check_file(file_path, repo_root))

    # Sort deterministically by file path, line number, and target string
    broken.sort(key=lambda x: (x[0], x[1], x[2]))

    for file_str, line_no, target in broken:
        print(f"{file_str}:{line_no} -> {target}")

    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
