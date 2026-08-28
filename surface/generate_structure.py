"""Generate full SDK structure artifacts for Python and TypeScript SDKs."""

from __future__ import annotations

import argparse
from pathlib import Path

from surface.extract.structure_python import extract_python_structure
from surface.extract.structure_typescript import extract_typescript_structure
from surface.render.structure import write_structure_artifacts

LAB_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PY_SDK = LAB_ROOT / "sdks" / "porto-sdk-python"
DEFAULT_TS_SDK = LAB_ROOT / "sdks" / "porto-sdk-typescript"
DEFAULT_OUT = Path(__file__).resolve().parent / "artifacts" / "structure"


def generate_python(*, sdk_root: Path, out_dir: Path, write_stubs: bool) -> list[str]:
    structure = extract_python_structure(sdk_root)
    return write_structure_artifacts(structure, out_dir=out_dir / "python", write_stubs=write_stubs)


def generate_typescript(*, sdk_root: Path, out_dir: Path, write_stubs: bool) -> list[str]:
    structure = extract_typescript_structure(sdk_root)
    return write_structure_artifacts(
        structure, out_dir=out_dir / "typescript", write_stubs=write_stubs
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate full SDK structure (declarations only) for both Porto SDKs.",
    )
    parser.add_argument("--python-sdk", type=Path, default=DEFAULT_PY_SDK)
    parser.add_argument("--typescript-sdk", type=Path, default=DEFAULT_TS_SDK)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--language", choices=("python", "typescript", "both"), default="both")
    parser.add_argument("--no-stubs", action="store_true", help="Skip per-module stub files")
    args = parser.parse_args(argv)

    written: list[str] = []
    if args.language in {"python", "both"}:
        written.extend(
            generate_python(
                sdk_root=args.python_sdk,
                out_dir=args.out,
                write_stubs=not args.no_stubs,
            )
        )
    if args.language in {"typescript", "both"}:
        written.extend(
            generate_typescript(
                sdk_root=args.typescript_sdk,
                out_dir=args.out,
                write_stubs=not args.no_stubs,
            )
        )

    print(f"Wrote {len(written)} artifacts under {args.out}")
    for path in written[:20]:
        print(f"  - {path}")
    if len(written) > 20:
        print(f"  ... and {len(written) - 20} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
