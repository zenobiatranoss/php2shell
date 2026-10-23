#!/usr/bin/env python3

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATTERNS = {
    "heap_use_after_free": re.compile(
        r"AddressSanitizer: heap-use-after-free", re.I
    ),
    "address_sanitizer": re.compile(r"AddressSanitizer", re.I),
    "memory_limit": re.compile(
        r"Allowed memory size of \d+ bytes exhausted", re.I
    ),
    "http_500": re.compile(r"HTTP/\d(?:\.\d)? 500", re.I),
    "segmentation_fault": re.compile(
        r"segmentation fault|signal 11|SIGSEGV", re.I
    ),
    "command_execution_claim": re.compile(
        r"(?:uid=\d+|gid=\d+|command executed successfully)", re.I
    ),
}


def analyze_file(path):
    try:
        content = path.read_text(errors="replace")
    except OSError as exc:
        return {
            "file": str(path.relative_to(ROOT)),
            "error": str(exc),
            "findings": [],
        }

    findings = [
        name
        for name, pattern in PATTERNS.items()
        if pattern.search(content)
    ]

    return {
        "file": str(path.relative_to(ROOT)),
        "findings": findings,
        "bytes": len(content.encode()),
    }


def main():
    files = sorted(
        path
        for path in ROOT.iterdir()
        if path.is_file() and path.suffix in {".log", ".txt"}
    )

    results = [analyze_file(path) for path in files]

    report = {
        "scope": "static analysis of local research evidence",
        "files_analyzed": len(results),
        "results": results,
        "limitations": [
            "Text matches do not independently prove exploitability.",
            "A command-output pattern is not proof of remote execution.",
            "Missing indicators do not prove the vulnerability is absent.",
        ],
    }

    output = json.dumps(report, indent=2)
    print(output)

    if "--json" in sys.argv:
        destination = ROOT / "evidence-analysis.json"
        destination.write_text(output + "\n")
        print(f"\nSaved report: {destination}")


if __name__ == "__main__":
    main()
