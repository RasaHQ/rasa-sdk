#!/usr/bin/env python

"""Extract the setuptools version pinned in poetry.lock."""

import pathlib
import re
import sys

poetry_lock = pathlib.Path(__file__).parent.parent / "poetry.lock"

if __name__ == "__main__":
    content = poetry_lock.read_text()
    match = re.search(
        r'\[\[package\]\]\s+name\s*=\s*"setuptools"\s+version\s*=\s*"([^"]+)"',
        content,
    )
    if match:
        print(match.group(1))
        sys.exit(0)
    print("Failed to find setuptools version in poetry.lock.", file=sys.stderr)
    sys.exit(1)
