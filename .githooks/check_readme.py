#!/usr/bin/env python3
"""pre-commit: README.md must carry the stamp of a Meta model and must not have been edited since (see the README)."""
import hashlib, re, subprocess, sys
text = open("README.md", encoding="utf-8").read()
m = re.search(r"\n*<!-- readme-author: (\S+) body-sha256: ([0-9a-f]{64}) -->\s*$", text)
if not m or not m.group(1).startswith(("muse-", "llama", "meta-")):
    sys.exit("README.md is not stamped by a Meta model: change it only with tools/readme_meta.py rewrite README.md")
body = text[:m.start()].rstrip("\n").replace("\r\n", "\n")
if hashlib.sha256(body.encode("utf-8")).hexdigest() != m.group(2):
    sys.exit("README.md was edited after the Meta model wrote it: run tools/readme_meta.py rewrite README.md")
