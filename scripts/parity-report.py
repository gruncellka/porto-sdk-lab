#!/usr/bin/env python3
"""
Report Python vs TypeScript BDD step coverage for @sdk porto-features.

Outputs docs/sdks/parity.md with per-feature step parity and gaps.

Usage (from Porto SDK Lab root):
  python scripts/parity-report.py
  python scripts/parity-report.py --check
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

FEATURES_SDK_DIR = (
    _REPO_ROOT / "resources" / "porto-features" / "porto_features" / "features" / "sdk"
)
PY_STEPS_DIR = _REPO_ROOT / "sdks" / "porto-sdk-python" / "tests" / "bdd" / "steps"
TS_STEPS_DIR = _REPO_ROOT / "sdks" / "porto-sdk-typescript" / "tests" / "bdd" / "steps"
REPORT_PATH = _REPO_ROOT / "docs" / "sdks" / "parity.md"
MANUAL_SECTION_MARKER = "## 0.0.1 behavior matrix"
GENERATED_SECTION_MARKER = "\n---\n\n"

STEP_PREFIX_RE = re.compile(r"^(?:Given|When|Then|And|But)\s+", re.IGNORECASE)
PY_STEP_RE = re.compile(
    r"@(?:given|when|then)\(\s*(?:parsers\.parse\(\s*)?([\"'])(.*?)\1",
    re.IGNORECASE | re.DOTALL,
)
TS_STEP_RE = re.compile(
    r"(?:Given|When|Then)\(\s*(?:/(.+?)/|['\"`]([^'\"`]+)['\"`])",
    re.IGNORECASE,
)
PLACEHOLDER_RE = re.compile(
    r'\{[^}]+\}|"[^"]*"|\'[^\']*\'|\b\d+\b',
)


@dataclass(frozen=True)
class StepCoverage:
    text: str
    normalized: str
    python: bool
    typescript: bool


def _normalize_step(text: str) -> str:
    cleaned = STEP_PREFIX_RE.sub("", text.strip())
    cleaned = PLACEHOLDER_RE.sub("*", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def _has_sdk_tag(feature_path: Path) -> bool:
    for line in feature_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "@sdk":
            return True
        if stripped.startswith("Feature:"):
            break
    return False


def _collect_feature_steps() -> dict[str, set[str]]:
    per_feature: dict[str, set[str]] = {}
    if not FEATURES_SDK_DIR.is_dir():
        return per_feature

    for feature_path in sorted(FEATURES_SDK_DIR.rglob("*.feature")):
        if not _has_sdk_tag(feature_path):
            continue
        rel = feature_path.relative_to(FEATURES_SDK_DIR).as_posix()
        steps: set[str] = set()
        for line in feature_path.read_text(encoding="utf-8").splitlines():
            match = STEP_PREFIX_RE.match(line.strip())
            if not match:
                continue
            steps.add(line.strip())
        if steps:
            per_feature[rel] = steps
    return per_feature


def _collect_python_steps() -> set[str]:
    patterns: set[str] = set()
    if not PY_STEPS_DIR.is_dir():
        return patterns
    for path in sorted(PY_STEPS_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for match in PY_STEP_RE.finditer(text):
            patterns.add(_normalize_step(match.group(2)))
    return patterns


def _regex_to_pattern(source: str) -> str:
    pattern = source
    pattern = re.sub(r"\(\?:[^)]+\)\??", "*", pattern)
    pattern = re.sub(r"\([^)]*\)", "*", pattern)
    pattern = pattern.replace("^", "").replace("$", "")
    pattern = re.sub(r"\\[dDsSwW.]", "*", pattern)
    pattern = pattern.replace("\\", "")
    pattern = re.sub(r"\s+", " ", pattern).strip().lower()
    return pattern


def _collect_typescript_steps() -> set[str]:
    patterns: set[str] = set()
    if not TS_STEPS_DIR.is_dir():
        return patterns
    for path in sorted(TS_STEPS_DIR.glob("*.ts")):
        text = path.read_text(encoding="utf-8")
        for match in TS_STEP_RE.finditer(text):
            regex = match.group(1)
            literal = match.group(2)
            if regex:
                patterns.add(_regex_to_pattern(regex))
            elif literal:
                patterns.add(_normalize_step(literal))
    return patterns


def _step_implemented(step: str, patterns: set[str]) -> bool:
    normalized = _normalize_step(step)
    if normalized in patterns:
        return True
    for pattern in patterns:
        if pattern == normalized:
            return True
        if "*" in pattern:
            regex = "^" + re.escape(pattern).replace("\\*", ".*") + "$"
            if re.match(regex, normalized):
                return True
    return False


def _normalize_report_for_check(text: str) -> str:
    return re.sub(
        r"`\d{4}-\d{2}-\d{2}T[^`]+Z` by `scripts/parity-report\.py`",
        "`<timestamp>` by `scripts/parity-report.py`",
        text,
    )


def _read_manual_prefix(path: Path) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    if MANUAL_SECTION_MARKER not in text:
        return ""
    head, _sep, _rest = text.partition(GENERATED_SECTION_MARKER)
    return head.rstrip() + "\n"


def build_report(manual_prefix: str = "") -> tuple[str, list[StepCoverage]]:
    feature_steps = _collect_feature_steps()
    python_patterns = _collect_python_steps()
    typescript_patterns = _collect_typescript_steps()

    all_steps: dict[str, StepCoverage] = {}
    for steps in feature_steps.values():
        for step in sorted(steps):
            normalized = _normalize_step(step)
            if normalized in all_steps:
                continue
            all_steps[normalized] = StepCoverage(
                text=step,
                normalized=normalized,
                python=_step_implemented(step, python_patterns),
                typescript=_step_implemented(step, typescript_patterns),
            )

    total = len(all_steps)
    both = sum(1 for row in all_steps.values() if row.python and row.typescript)
    py_only = sum(1 for row in all_steps.values() if row.python and not row.typescript)
    ts_only = sum(1 for row in all_steps.values() if row.typescript and not row.python)
    missing = sum(1 for row in all_steps.values() if not row.python and not row.typescript)

    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if manual_prefix:
        lines = [
            manual_prefix.rstrip(),
            "---",
            "",
            f"Generated at `{generated_at}` by `scripts/parity-report.py`.",
            "",
            "Compares porto-features `@sdk` scenario steps against Python pytest-bdd",
            "and TypeScript Cucumber step definitions in both SDK repos.",
            "",
            "The generated inventory below is a step-string dump; the **0.0.1 behavior matrix**",
            "above is the semantic contract for the freeze.",
            "",
        ]
    else:
        lines = [
            "# BDD step parity report (`@sdk`)",
            "",
            f"Generated at `{generated_at}` by `scripts/parity-report.py`.",
            "",
            "Compares porto-features `@sdk` scenario steps against Python pytest-bdd",
            "and TypeScript Cucumber step definitions in both SDK repos.",
            "",
        ]

    lines.extend(
        [
            "## Summary",
            "",
            f"- Features scanned: **{len(feature_steps)}**",
            f"- Unique steps: **{total}**",
            f"- Covered in both SDKs: **{both}**",
            f"- Python only: **{py_only}**",
            f"- TypeScript only: **{ts_only}**",
            f"- Missing in both SDKs: **{missing}**",
            "",
        ]
    )

    if missing:
        lines.extend(["## Missing in both SDKs", ""])
        for row in sorted(all_steps.values(), key=lambda item: item.normalized):
            if not row.python and not row.typescript:
                lines.append(f"- `{row.text}`")
        lines.append("")

    mismatches = [
        row
        for row in all_steps.values()
        if row.python != row.typescript and (row.python or row.typescript)
    ]
    if mismatches:
        lines.extend(["## Python / TypeScript mismatch", ""])
        lines.append("| Step | Python | TypeScript |")
        lines.append("|------|:------:|:----------:|")
        for row in sorted(mismatches, key=lambda item: item.normalized):
            py = "yes" if row.python else "no"
            ts = "yes" if row.typescript else "no"
            lines.append(f"| `{row.text}` | {py} | {ts} |")
        lines.append("")

    lines.extend(["## Per-feature steps", ""])
    for rel, steps in sorted(feature_steps.items()):
        lines.append(f"### `{rel}`")
        lines.append("")
        for step in sorted(steps):
            row = all_steps[_normalize_step(step)]
            py = "yes" if row.python else "no"
            ts = "yes" if row.typescript else "no"
            lines.append(f"- `{step}` — Py: **{py}**, TS: **{ts}**")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n", list(all_steps.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate @sdk BDD step parity report.")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPORT_PATH,
        help="Markdown output path (default: docs/sdks/parity.md)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 when report would change or any @sdk step lacks both SDK implementations",
    )
    args = parser.parse_args()

    manual_prefix = _read_manual_prefix(args.output)
    report, rows = build_report(manual_prefix)
    missing_both = [row for row in rows if not row.python and not row.typescript]
    mismatched = [row for row in rows if row.python != row.typescript]

    existing = args.output.read_text(encoding="utf-8") if args.output.is_file() else ""
    changed = _normalize_report_for_check(existing) != _normalize_report_for_check(report)

    if args.check:
        if missing_both:
            print(
                f"❌ Parity gaps: missing_both={len(missing_both)}",
                file=sys.stderr,
            )
            return 1
        if mismatched:
            print(
                f"⚠️  Step wording drift: mismatched={len(mismatched)} (BDD green on both SDKs)",
            )
        if changed:
            print(
                f"❌ {args.output} is stale. Run: python scripts/parity-report.py", file=sys.stderr
            )
            return 1
        print(f"✅ {args.output} is up to date and parity is clean.")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"✅ Wrote parity report to {args.output}")
    if missing_both:
        print(f"⚠️  {len(missing_both)} step(s) missing in both SDKs")
    if mismatched:
        print(f"⚠️  {len(mismatched)} step(s) differ between Python and TypeScript")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
