"""Flag verbose names. One word is the default; two is normal; four or more fails unless baselined.

Does not rename, and does not look at wire values or test names.
A definition line (or the line above it) may say `naming: ok` to allow a long name.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
BASELINE = LAB / "scripts" / "naming-baseline.txt"
ROOTS = (
    ("py", LAB / "sdks" / "porto-sdk-python" / "porto_sdk"),
    ("ts", LAB / "sdks" / "porto-sdk-typescript" / "src"),
)

_DEF = re.compile(
    r"""
    ^[ \t]*(?:export[ \t]+)?(?:declare[ \t]+)?(?:async[ \t]+)?
    (?:function|class|interface|enum|type|def)[ \t]+([A-Za-z_][A-Za-z0-9_]*)
    |
    ^[ \t]*(?:export[ \t]+)?(?:const|let)[ \t]+([A-Za-z_][A-Za-z0-9_]*)
    |
    ^[ \t]*([A-Z][A-Z0-9_]{2,})[ \t]*(?::[^=\n]+)?=
    """,
    re.VERBOSE,
)
_SKIP_DIRS = {"__pycache__", "node_modules", "dist", ".venv"}


@dataclass(frozen=True)
class Hit:
    kind: str  # symbol | path
    key: str
    detail: str


def words(name: str) -> list[str]:
    name = name.strip("_")
    if not name:
        return []
    split = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    split = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", split)
    return [part for part in re.split(r"[_\-]+", split) if part]


def scan(root: Path, label: str) -> list[Hit]:
    hits: list[Hit] = []
    if not root.is_dir():
        return hits
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".ts"}:
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if (
            path.name.endswith(".d.ts")
            or path.name.endswith(".test.ts")
            or path.name.startswith("test_")
        ):
            continue
        rel = path.relative_to(root).as_posix()
        parent: set[str] = set()
        for part in Path(rel).parts[:-1]:
            parent.update(word.lower() for word in words(part))
        repeated = [
            word for word in words(path.stem) if word.lower() in parent and word.lower() != "index"
        ]
        if repeated:
            hits.append(Hit("path", f"{label} {rel}", f"repeats {', '.join(repeated)}"))
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for index, line in enumerate(lines):
            if line.lstrip().startswith(("import ", "from ", "//", "#", "*", "/*")):
                continue
            match = _DEF.search(line)
            if not match:
                continue
            name = next(group for group in match.groups() if group)
            if name.startswith("test_") or name.startswith("__"):
                continue
            count = len(words(name))
            if count < 3:
                continue
            window = line
            if index:
                window = lines[index - 1] + line
            if "naming: ok" in window:
                continue
            hits.append(Hit("symbol", name, f"{label} {rel}:{index + 1} {name} ({count} words)"))
    return hits


def load_baseline(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    allowed: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        kind, _, key = line.partition(" ")
        if kind in {"symbol", "path"} and key:
            allowed.add(f"{kind} {key}")
    return allowed


def failures(hits: list[Hit], allowed: set[str]) -> list[Hit]:
    bad: list[Hit] = []
    for hit in hits:
        if hit.kind == "symbol" and len(words(hit.key)) == 3:
            continue
        token = f"{hit.kind} {hit.key}"
        if token not in allowed:
            bad.append(hit)
    return bad


def warnings(hits: list[Hit]) -> int:
    return sum(1 for hit in hits if hit.kind == "symbol" and len(words(hit.key)) == 3)


def render_baseline(hits: list[Hit]) -> str:
    lines = [
        "# Existing long names. New 4+ word definitions and repeated filenames fail.",
        "# symbol <name>",
        "# path <label> <relative/path>",
        "# A definition may also opt out with `naming: ok` on that line or the line above.",
    ]
    seen: set[str] = set()
    for hit in sorted(hits, key=lambda item: (item.kind, item.key)):
        if hit.kind == "symbol" and len(words(hit.key)) < 4:
            continue
        token = f"{hit.kind} {hit.key}"
        if token in seen:
            continue
        seen.add(token)
        lines.append(token)
    return "\n".join(lines) + "\n"


def check(roots: tuple[tuple[str, Path], ...] = ROOTS, baseline: Path = BASELINE) -> list[Hit]:
    hits: list[Hit] = []
    for label, root in roots:
        hits.extend(scan(root, label))
    return failures(hits, load_baseline(baseline))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flag verbose SDK names.")
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    args = parser.parse_args(argv)
    hits: list[Hit] = []
    for label, root in ROOTS:
        if not root.is_dir():
            print(f"naming: missing {root}", file=sys.stderr)
            return 1
        hits.extend(scan(root, label))
    if args.write_baseline:
        args.baseline.write_text(render_baseline(hits), encoding="utf-8")
        print(f"naming: wrote {args.baseline}")
        return 0
    bad = failures(hits, load_baseline(args.baseline))
    print(f"naming: 3-word definitions: {warnings(hits)} (warning)")
    if not bad:
        print("naming: ok")
        return 0
    print(f"naming: {len(bad)} new long name(s):", file=sys.stderr)
    for hit in bad:
        print(f"  {hit.detail}", file=sys.stderr)
    print("Add `naming: ok`, or record the name in scripts/naming-baseline.txt.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
