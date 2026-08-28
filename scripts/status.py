#!/usr/bin/env python3
"""Lab status checking and reporting."""

import sys

from lib.lab_state import (
    check_resources,
    check_sdks,
    check_submodules_initialized,
    check_venv_exists,
)
from lib.workspace import (
    get_workspace_root,
)


def print_status() -> int:
    """Print lab status report.

    Returns:
        Exit code (0 = all good, 1 = issues found).
    """
    workspace_root = get_workspace_root()
    has_issues = False

    print("📊 Porto SDK Lab Status")
    print("=" * 50)
    print()

    # Check Python environment
    print("🐍 Python Environment:")
    if check_venv_exists(workspace_root):
        print("  ✅ Virtual environment: exists")
    else:
        print("  ❌ Virtual environment: not found")
        print("     Run: porto setup")
        has_issues = True
    print()

    # Check submodules
    print("📦 Git Submodules:")
    submodule_status = check_submodules_initialized(workspace_root)
    if submodule_status.get("_error") == "error":
        print("  ⚠️  Could not check submodule status (git not found?)")
    elif not submodule_status:
        print("  ℹ️  No .gitmodules file found")
    else:
        all_ok = True
        for path, status in submodule_status.items():
            if path == "_error":
                continue
            if status == "ok":
                print(f"  ✅ {path}")
            elif status == "missing":
                print(f"  ❌ {path} (not initialized)")
                print("     Run: porto setup --repos-only")
                all_ok = False
                has_issues = True
            elif status == "modified":
                print(f"  ⚠️  {path} (has local changes)")
            else:
                print(f"  ⚠️  {path} (unknown status: {status})")
        if all_ok and submodule_status:
            print("  ✅ All submodules initialized")
    print()

    # Check SDKs
    print("🔧 SDKs:")
    sdks = check_sdks(workspace_root)
    if not sdks:
        print("  ❌ sdks/ directory not found")
        print("     Run: porto setup --repos-only")
        has_issues = True
    else:
        all_complete = True
        for sdk_name, is_complete in sdks.items():
            if is_complete:
                print(f"  ✅ {sdk_name}")
            else:
                print(f"  ⚠️  {sdk_name} (incomplete)")
                all_complete = False
        if all_complete:
            print("  ✅ All SDKs are complete")
    print()

    # Check resources
    print("📚 Resources:")
    resources = check_resources(workspace_root)
    if not resources:
        print("  ❌ resources/ directory not found")
        print("     Run: porto setup --repos-only")
        has_issues = True
    else:
        for resource_name in resources:
            print(f"  ✅ {resource_name}")
        if resources:
            print(f"  ✅ {len(resources)} resource(s) available")
    print()

    return 1 if has_issues else 0


def main() -> int:
    """Main entry point for status command.

    Returns:
        Exit code (0 = all good, 1 = issues found).
    """
    return print_status()


if __name__ == "__main__":
    sys.exit(main())
