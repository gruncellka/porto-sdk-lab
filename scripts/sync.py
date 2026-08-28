#!/usr/bin/env python3
"""Make submodule folders match the commits the Lab repo points to.

The Lab repo stores which commit each submodule is at (the "pin"). Your submodule
folders on disk might be at a different commit (e.g. you checked out a branch).

Default (no --remote): check out in each submodule the commit the Lab points to.
Does NOT fetch "latest" from remote — only aligns your disk to the pins.
Run after git pull so your folders match the (possibly new) pins.

Optional --remote: fetch latest from remote default branch and move the pins;
then you commit the new refs in Lab (make sm-sync-remote).

The --recursive flag is used for consistency (SDKs have no nested submodules; they use npm/pip packages).

Structure:
    porto-sdk-lab/
    ├── resources/porto-data          <- Level 1 submodule (dev/Lab only)
    ├── resources/porto-features       <- Level 1 submodule (dev/Lab only)
    └── sdks/                         <- Level 1 submodules (porto-sdk-python, porto-sdk-typescript)

See CONTRIBUTING.md for full explanation.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import uuid
from pathlib import Path

from lib.submodules import submodules_in_gitmodules_but_not_in_index
from lib.workspace import get_workspace_root


def get_submodule_status(workspace_root) -> list[dict]:
    """Get status of all submodules including nested ones.

    Returns:
        List of dicts with submodule info: path, commit, status.
    """
    result = subprocess.run(
        ["git", "submodule", "status", "--recursive"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return []

    submodules = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue

        # Format: " <commit> <path> (<branch>)" or "-<commit> <path>" (uninitialized)
        # or "+<commit> <path>" (modified)
        status_char = line[0] if line[0] in "-+ " else " "
        parts = line[1:].strip().split()

        if len(parts) >= 2:
            commit = parts[0]
            path = parts[1]

            status = "ok"
            if status_char == "-":
                status = "uninitialized"
            elif status_char == "+":
                status = "modified"

            submodules.append({"path": path, "commit": commit[:8], "status": status})

    return submodules


def print_submodule_status(submodules: list[dict], title: str) -> None:
    """Print formatted submodule status."""
    print(f"\n{title}")
    print("-" * 60)

    if not submodules:
        print("  (no submodules found)")
        return

    # Group by level (nested vs root)
    root_level = []
    nested = []

    for sm in submodules:
        if sm["path"].count("/") >= 2:  # e.g., sdks/porto-sdk-python/resources/...
            nested.append(sm)
        else:
            root_level.append(sm)

    print("  Root-level submodules:")
    for sm in root_level:
        icon = "✓" if sm["status"] == "ok" else "!" if sm["status"] == "modified" else "?"
        print(f"    [{icon}] {sm['path']:<40} @ {sm['commit']}")

    if nested:
        print("\n  Nested submodules (inside SDKs):")
        for sm in nested:
            icon = "✓" if sm["status"] == "ok" else "!" if sm["status"] == "modified" else "?"
            print(f"    [{icon}] {sm['path']:<40} @ {sm['commit']}")


def get_submodule_paths(workspace_root: Path) -> list[str]:
    """Return submodule paths from git status output."""
    result = subprocess.run(
        ["git", "submodule", "status", "--recursive"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []

    paths: list[str] = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line[1:].strip().split()
        if len(parts) >= 2:
            paths.append(parts[1])
    return paths


def is_submodule_dirty(workspace_root: Path, path: str) -> bool:
    """Return True when a submodule has local changes."""
    result = subprocess.run(
        ["git", "-C", path, "status", "--porcelain"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    return bool(result.stdout.strip())


def stash_submodule_changes(workspace_root: Path, path: str) -> str | None:
    """Stash local changes in submodule and return created stash ref."""
    marker = f"porto-sdk-lab-autostash-{uuid.uuid4()}"

    create = subprocess.run(
        ["git", "-C", path, "stash", "push", "-u", "-m", marker],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if create.returncode != 0:
        return None

    stash_list = subprocess.run(
        ["git", "-C", path, "stash", "list", "--format=%gd%x09%s"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if stash_list.returncode != 0:
        return None

    for line in stash_list.stdout.strip().split("\n"):
        if not line.strip():
            continue
        ref_and_subject = line.split("\t", 1)
        if len(ref_and_subject) != 2:
            continue
        ref, subject = ref_and_subject
        # git stash formats subject as "On <branch>: <message>".
        # We only control the <message> marker, so match by suffix.
        if subject == marker or subject.endswith(marker):
            return ref
    return None


def restore_submodule_stash(workspace_root: Path, path: str, stash_ref: str) -> bool:
    """Restore previously stashed changes into submodule."""
    apply_result = subprocess.run(
        ["git", "-C", path, "stash", "apply", stash_ref],
        cwd=workspace_root,
        check=False,
    )
    if apply_result.returncode != 0:
        return False

    subprocess.run(
        ["git", "-C", path, "stash", "drop", stash_ref],
        cwd=workspace_root,
        check=False,
    )
    return True


def main() -> int:
    """Main entry point for sync operations.

    Default (no --remote): update submodules to the commits RECORDED in the Lab repo.
    With --remote: update to latest on remote default branch (then commit refs in Lab).
    """
    parser = argparse.ArgumentParser(
        description="Sync submodules to recorded commits (default) or to remote branch tip (--remote)."
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Update to latest commit on remote default branch (not recorded SHA); then commit refs in Lab.",
    )
    parser.add_argument(
        "--autostash",
        action="store_true",
        help="Temporarily stash dirty submodule changes before update and restore them afterwards.",
    )
    args = parser.parse_args()
    use_remote = args.remote
    use_autostash = args.autostash

    workspace_root = get_workspace_root()

    print("=" * 60)
    if use_remote:
        print("  SUBMODULE UPDATE --remote - update to remote default branch (usually main)")
    else:
        print("  SUBMODULE UPDATE - make folders match the commits Lab points to")
    print("=" * 60)
    print()
    if use_remote:
        print("This will:")
        print("  1. Initialize any uninitialized submodules")
        print(
            "  2. Fetch and check out latest on each submodule's remote default branch (usually main)"
        )
        print("  3. Lab repo will show modified submodule refs → commit them to update pins")
    else:
        print("This will:")
        print("  1. Initialize any uninitialized submodules")
        print(
            "  2. Check out in each submodule the commit the Lab repo points to (no remote fetch)"
        )
        print("  3. Your disk will match the pins; run after git pull to get new pins")
    print()
    print("This will NOT:")
    print("  - Commit anything in the Lab repo")
    print("  - Push to any remote")
    if use_autostash:
        print("  - Lose your local submodule edits (they are stashed and restored)")
    print()

    gitmodules_path = workspace_root / ".gitmodules"
    if not gitmodules_path.exists():
        print("⚠️  .gitmodules not found, nothing to sync")
        return 0

    if not (workspace_root / ".git").exists():
        print("⚠️  Not in a git repository, cannot sync submodules")
        return 0

    # Detect submodules that are in .gitmodules but not in the index (never added properly).
    # Those will not be cloned by "git submodule update --init".
    unregistered = submodules_in_gitmodules_but_not_in_index(workspace_root)
    if unregistered:
        print()
        print(
            "⚠️  Some submodules are listed in .gitmodules but not registered in the repo (no gitlink)."
        )
        print("   They will not be cloned by 'make sm-sync' until someone adds them once:")
        print()
        for sm in unregistered:
            path = sm.get("path", "")
            url = sm.get("url", "")
            print(f"   • {path}")
            print(f"     Fix: git submodule add {url} {path}")
            if not (workspace_root / path).exists():
                print(f"     (Folder {path} will appear after the add and commit.)")
        print()
        print(
            "   Then commit and push the Lab repo so others get the new submodule on next pull + sm-sync."
        )
        print()

    # Show status before
    submodules_before = get_submodule_status(workspace_root)
    print_submodule_status(submodules_before, "📋 Current state (before sync)")

    # Build command: --init --recursive always; add --remote if requested
    cmd = ["git", "submodule", "update", "--init", "--recursive"]
    if use_remote:
        cmd.insert(3, "--remote")  # after "update"

    stashed_submodules: list[tuple[str, str]] = []
    restore_errors: list[str] = []
    if use_autostash:
        print("\n🧰 AUTOSTASH enabled - scanning dirty submodules...")
        for path in get_submodule_paths(workspace_root):
            if not is_submodule_dirty(workspace_root, path):
                continue
            stash_ref = stash_submodule_changes(workspace_root, path)
            if stash_ref:
                stashed_submodules.append((path, stash_ref))
                print(f"   • stashed {path} ({stash_ref})")
            else:
                print(f"   • warning: could not stash {path}; continuing")
        if not stashed_submodules:
            print("   No dirty submodules found")

    print("\n📥 Updating submodules...")
    print(f"   Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=workspace_root, check=False)

    if use_autostash and stashed_submodules:
        print("\n📤 Restoring autostashed changes...")
        # Restore in reverse order to better match user expectations.
        for path, stash_ref in reversed(stashed_submodules):
            restored = restore_submodule_stash(workspace_root, path, stash_ref)
            if restored:
                print(f"   • restored {path} ({stash_ref})")
            else:
                restore_errors.append(path)
                print(
                    f"   • warning: could not restore {path}; stash kept as {stash_ref}",
                    file=sys.stderr,
                )

    if result.returncode != 0:
        print("\n⚠️  Some submodules may have failed to update", file=sys.stderr)
        if use_remote:
            print("   This can happen if: network issues, or remote default branch doesn't exist")
        else:
            print(
                "   This can happen if: recorded commit not fetched yet (try git submodule update --init --recursive)"
            )

    if restore_errors:
        print(
            "\n⚠️  Some stashes could not be reapplied cleanly; resolve conflicts manually and re-apply stash in affected submodules.",
            file=sys.stderr,
        )

    # Show status after
    submodules_after = get_submodule_status(workspace_root)
    print_submodule_status(submodules_after, "📋 Updated state (after sync)")

    # Compare before/after
    print("\n" + "=" * 60)
    changed = []
    for after in submodules_after:
        for before in submodules_before:
            if after["path"] == before["path"] and after["commit"] != before["commit"]:
                changed.append(f"  {after['path']}: {before['commit']} → {after['commit']}")

    if changed:
        print("📝 Submodule checkouts changed:")
        for change in changed:
            print(change)
        if use_remote:
            print()
            print("⚠️  NEXT STEP: Commit the updated references in the Lab repo:")
            print()
            print("    git add resources/ sdks/")
            print('    git commit -m "chore: update submodule references"')
            print("    git push")
            print()
    else:
        print("✅ All submodules already at target commits - no changes needed")

    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
