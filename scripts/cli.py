#!/usr/bin/env python3
"""Porto lab CLI - thin dispatcher to script modules."""

import argparse
import sys

# Import script modules
import setup
import status
import sync
from lib.make_runner import run_make


def _setup_wrapper(args: argparse.Namespace) -> int:
    """Wrapper to call setup.main() with proper arguments."""
    # Temporarily modify sys.argv to pass arguments to setup.py
    original_argv = sys.argv[:]
    try:
        sys.argv = ["setup.py"]
        if args.repos_only:
            sys.argv.append("--repos-only")
        elif args.all:
            sys.argv.append("--all")
        return setup.main()
    finally:
        sys.argv = original_argv


def main() -> int:
    """Main CLI entry point - dispatches to appropriate script module."""
    parser = argparse.ArgumentParser(
        prog="porto",
        description="Porto SDK Lab management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  porto setup              # Setup Python environment
  porto setup --repos-only # Initialize submodules only
  porto setup --all        # Complete setup
  porto status             # Show lab status
  porto sync               # Sync git submodules
  porto test --python      # Run Python tests only
  porto clean --all        # Clean everything

For more commands, see: make help
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Setup command - calls setup.py
    setup_parser = subparsers.add_parser("setup", help="Setup lab")
    setup_group = setup_parser.add_mutually_exclusive_group()
    setup_group.add_argument(
        "--repos-only",
        action="store_true",
        help="Initialize git submodules only",
    )
    setup_group.add_argument(
        "--all",
        action="store_true",
        help="Complete setup (repos + environment)",
    )
    setup_parser.set_defaults(func=_setup_wrapper)

    # Sync command - calls sync.py
    sync_parser = subparsers.add_parser("sync", help="Sync git submodules")
    sync_parser.set_defaults(func=lambda _: sync.main())

    # Status command - calls status.py
    status_parser = subparsers.add_parser("status", help="Show lab status")
    status_parser.set_defaults(func=lambda _: status.main())

    # Test command - delegates to make
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_group = test_parser.add_mutually_exclusive_group()
    test_group.add_argument("--python", action="store_true", help="Python tests only")
    test_group.add_argument("--typescript", action="store_true", help="TypeScript tests only")
    test_group.add_argument("--bdd", action="store_true", help="BDD tests only")
    test_group.add_argument("--all", action="store_true", help="All tests")
    test_parser.set_defaults(
        func=lambda args: run_make(
            "test-packages-py"
            if args.python
            else "test-packages-ts"
            if args.typescript
            else "test-packages-bdd"
            if args.bdd
            else "test-all"
            if args.all
            else "test",
            check=False,
        )
    )

    # Clean command - delegates to make
    clean_parser = subparsers.add_parser("clean", help="Clean lab")
    clean_group = clean_parser.add_mutually_exclusive_group()
    clean_group.add_argument("--all", action="store_true", help="Clean everything")
    clean_group.add_argument("--deps", action="store_true", help="Clean dependencies")
    clean_group.add_argument("--repos", action="store_true", help="Remove submodules")
    clean_parser.set_defaults(
        func=lambda args: run_make(
            "clean-all"
            if args.all
            else "clean-deps"
            if args.deps
            else "clean-repos"
            if args.repos
            else "clean",
            check=False,
        )
    )

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    result = args.func(args)
    return int(result) if result is not None else 0


if __name__ == "__main__":
    sys.exit(main())
