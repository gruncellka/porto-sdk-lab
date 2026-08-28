#!/usr/bin/env python3
"""
MVP observer runner for lab commands.

Captures process lifecycle, stdout/stderr, exit code, and summary artifacts.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import IO

OBSERVER_VERSION = "0.2.0"


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def run_id_prefix(dt: datetime) -> str:
    return dt.strftime("%Y%m%d-%H%M%S")


def build_run_id(dt: datetime) -> str:
    return f"{run_id_prefix(dt)}-{secrets.token_hex(2)[:3]}"


SECRET_PATTERNS = [
    # Generic env/kv style secrets
    re.compile(
        r"(?i)\b(password|passwd|secret|token|api[_-]?key|client[_-]?secret)\b\s*([:=])\s*([^\s,;]+)"
    ),
    # Authorization header/value
    re.compile(r"(?i)\bauthorization\b\s*([:=])\s*([^\s,;]+(?:\s+[^\s,;]+)?)"),
    # Bearer token fragments
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]+"),
]


def redact(text: str) -> str:
    redacted = text

    def _replace_kv(match: re.Match[str]) -> str:
        key = match.group(1)
        sep = match.group(2)
        return f"{key}{sep}[REDACTED]"

    def _replace_auth(match: re.Match[str]) -> str:
        sep = match.group(1)
        return f"authorization{sep}[REDACTED]"

    redacted = SECRET_PATTERNS[0].sub(_replace_kv, redacted)
    redacted = SECRET_PATTERNS[1].sub(_replace_auth, redacted)
    redacted = SECRET_PATTERNS[2].sub("Bearer [REDACTED]", redacted)
    return redacted


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _merge_summary_with_metadata(run_dir: Path, summary: dict) -> dict:
    metadata_path = run_dir / "metadata.json"
    if not metadata_path.exists():
        return summary
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return summary
    merged = dict(summary)
    merged["experiment"] = metadata
    for key in (
        "profile",
        "cases_total",
        "cases_passed",
        "cases_failed",
        "estimated_spend_cents",
        "dry_run",
        "preflight_ok",
    ):
        if key in metadata:
            merged[key] = metadata[key]
    return merged


def append_jsonl(file_obj: IO[str], payload: dict) -> None:
    file_obj.write(json.dumps(payload, separators=(",", ":")) + "\n")
    file_obj.flush()


def detect_sdk_language(command: list[str], label: str) -> str:
    lowered = " ".join(command + [label]).lower()
    if "python" in lowered or ".py" in lowered:
        return "python"
    if "typescript" in lowered or "ts:" in lowered or ".ts" in lowered:
        return "typescript"
    return "unknown"


def detect_script(command: list[str], label: str) -> str | None:
    if ":" in label:
        _, tail = label.split(":", 1)
        if tail:
            return tail
    if command:
        maybe = command[-1]
        if maybe.endswith(".py") or maybe.endswith(".ts"):
            return maybe
    return None


def get_git_commit(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root),
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip() or "unknown"
    except OSError:
        pass
    return "unknown"


def prune_runs(runs_root: Path, keep_last_runs: int) -> int:
    if keep_last_runs <= 0:
        return 0
    run_dirs = sorted(
        [p for p in runs_root.iterdir() if p.is_dir()],
        key=lambda p: p.name,
    )
    if len(run_dirs) <= keep_last_runs:
        return 0

    to_delete = run_dirs[: len(run_dirs) - keep_last_runs]
    deleted = 0
    for path in to_delete:
        shutil.rmtree(path, ignore_errors=True)
        deleted += 1
    return deleted


def stream_reader(
    *,
    stream_name: str,
    input_stream: IO[str],
    output_file: IO[str],
    process_events: IO[str],
    run_id: str,
) -> None:
    try:
        for raw_line in input_stream:
            safe_line = redact(raw_line.rstrip("\n"))
            try:
                output_file.write(safe_line + "\n")
                output_file.flush()
            except ValueError:
                # Parent closed file during shutdown; stop reader quietly.
                return

            try:
                append_jsonl(
                    process_events,
                    {
                        "ts": utc_iso(utc_now()),
                        "run_id": run_id,
                        "event": "process_output",
                        "stream": stream_name,
                        "line": safe_line,
                    },
                )
            except ValueError:
                return

            if stream_name == "stdout":
                print(safe_line, flush=True)
            else:
                print(safe_line, file=sys.stderr, flush=True)
    except ValueError:
        # Pipe closed while draining subprocess output during shutdown.
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Wrap command execution and write lab observer artifacts."
    )
    parser.add_argument(
        "--artifacts-root",
        default="labs/experiments",
        help="Experiments root directory (default: labs/experiments)",
    )
    parser.add_argument(
        "--label",
        default="lab-observer-run",
        help="Human-readable run label for summary metadata",
    )
    parser.add_argument(
        "--keep-last-runs",
        type=int,
        default=int(os.environ.get("OBSERVER_KEEP_LAST_RUNS", "30")),
        help="Retention: keep only last N runs (0 disables pruning; default: 30)",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to execute, e.g. -- ./scripts/labs/run/py.sh example_basic.py",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("Error: missing command to execute.", file=sys.stderr)
        print("Example: observers/runner.py -- ./scripts/labs/run/py.sh", file=sys.stderr)
        return 2

    repo_root = Path(__file__).resolve().parents[3]
    artifacts_root = (repo_root / args.artifacts_root).resolve()
    started_at = utc_now()
    runs_root = artifacts_root / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    run_id = ""
    run_dir = runs_root
    created = False
    for _ in range(8):
        run_id = build_run_id(started_at)
        candidate = runs_root / run_id
        try:
            candidate.mkdir(parents=False, exist_ok=False)
            run_dir = candidate
            created = True
            break
        except FileExistsError:
            continue
    if not created:
        run_id = f"{run_id_prefix(started_at)}-{secrets.token_hex(4)}"
        run_dir = runs_root / run_id
        run_dir.mkdir(parents=False, exist_ok=False)

    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    process_path = run_dir / "process.jsonl"
    summary_path = run_dir / "summary.json"

    with (
        stdout_path.open("w", encoding="utf-8") as stdout_file,
        stderr_path.open("w", encoding="utf-8") as stderr_file,
        process_path.open("w", encoding="utf-8") as process_file,
    ):
        append_jsonl(
            process_file,
            {
                "ts": utc_iso(started_at),
                "run_id": run_id,
                "event": "run_started",
                "label": args.label,
                "cwd": str(repo_root),
                "command": command,
            },
        )

        try:
            process_env = os.environ.copy()
            process_env["OBSERVER_RUN_ID"] = run_id
            process_env["OBSERVER_RUN_DIR"] = str(run_dir)
            process_env["OBSERVER_ARTIFACTS_ROOT"] = str(artifacts_root)
            process = subprocess.Popen(
                command,
                cwd=str(repo_root),
                env=process_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            append_jsonl(
                process_file,
                {
                    "ts": utc_iso(utc_now()),
                    "run_id": run_id,
                    "event": "process_started",
                    "pid": process.pid,
                },
            )
        except OSError as exc:
            sdk_language = detect_sdk_language(command, args.label)
            script = detect_script(command, args.label)
            git_commit = get_git_commit(repo_root)
            append_jsonl(
                process_file,
                {
                    "ts": utc_iso(utc_now()),
                    "run_id": run_id,
                    "event": "run_failed_to_start",
                    "error": redact(str(exc)),
                },
            )
            write_json(
                summary_path,
                {
                    "run_id": run_id,
                    "label": args.label,
                    "started_at": utc_iso(started_at),
                    "finished_at": utc_iso(utc_now()),
                    "duration_seconds": 0,
                    "status": "failed_to_start",
                    "exit_code": 127,
                    "observer_version": OBSERVER_VERSION,
                    "sdk_language": sdk_language,
                    "script": script,
                    "git_commit": git_commit,
                    "command": command,
                    "cwd": str(repo_root),
                },
            )
            return 127

        assert process.stdout is not None
        assert process.stderr is not None

        stdout_thread = threading.Thread(
            target=stream_reader,
            kwargs={
                "stream_name": "stdout",
                "input_stream": process.stdout,
                "output_file": stdout_file,
                "process_events": process_file,
                "run_id": run_id,
            },
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=stream_reader,
            kwargs={
                "stream_name": "stderr",
                "input_stream": process.stderr,
                "output_file": stderr_file,
                "process_events": process_file,
                "run_id": run_id,
            },
            daemon=True,
        )

        stdout_thread.start()
        stderr_thread.start()

        interrupted = False
        try:
            return_code = process.wait()
        except KeyboardInterrupt:
            interrupted = True
            print("\nInterrupted. Stopping observed command...", file=sys.stderr, flush=True)
            append_jsonl(
                process_file,
                {
                    "ts": utc_iso(utc_now()),
                    "run_id": run_id,
                    "event": "run_interrupted",
                    "signal": "SIGINT",
                },
            )
            with contextlib.suppress(OSError):
                process.send_signal(signal.SIGINT)
            try:
                return_code = process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    return_code = process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    return_code = process.wait()
            except KeyboardInterrupt:
                process.kill()
                return_code = process.wait()
                interrupted = True

        stdout_thread.join()
        stderr_thread.join()
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()
        append_jsonl(
            process_file,
            {
                "ts": utc_iso(utc_now()),
                "run_id": run_id,
                "event": "process_exit",
                "pid": process.pid,
                "exit_code": return_code,
            },
        )

        finished_at = utc_now()
        duration_seconds = round((finished_at - started_at).total_seconds(), 3)
        status = "interrupted" if interrupted else "passed" if return_code == 0 else "failed"
        sdk_language = detect_sdk_language(command, args.label)
        script = detect_script(command, args.label)
        git_commit = get_git_commit(repo_root)

        append_jsonl(
            process_file,
            {
                "ts": utc_iso(finished_at),
                "run_id": run_id,
                "event": "run_finished",
                "status": status,
                "exit_code": return_code,
                "duration_seconds": duration_seconds,
            },
        )

        write_json(
            summary_path,
            _merge_summary_with_metadata(
                run_dir,
                {
                    "run_id": run_id,
                    "label": args.label,
                    "started_at": utc_iso(started_at),
                    "finished_at": utc_iso(finished_at),
                    "duration_seconds": duration_seconds,
                    "status": status,
                    "exit_code": return_code,
                    "observer_version": OBSERVER_VERSION,
                    "sdk_language": sdk_language,
                    "script": script,
                    "git_commit": git_commit,
                    "command": command,
                    "cwd": str(repo_root),
                },
            ),
        )

    latest_link = artifacts_root / "latest"
    try:
        if latest_link.is_symlink() or latest_link.exists():
            latest_link.unlink()
        os.symlink(run_dir, latest_link, target_is_directory=True)
    except OSError:
        # Best-effort on platforms/filesystems where symlink creation can fail.
        pass

    deleted_runs = prune_runs(runs_root, args.keep_last_runs)
    if deleted_runs > 0:
        print(f"Retention: deleted {deleted_runs} old run(s)")

    print(f"Artifacts written to: {run_dir}")
    print(f"Summary: {summary_path}")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
