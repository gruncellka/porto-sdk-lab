"""Tests for scripts/check_gitignore.py."""

from __future__ import annotations

import scripts.check_gitignore as check_gitignore


def test_allowlist_paths_not_flagged():
    paths = [
        "labs/experiments/runs/.gitkeep",
        "surface/artifacts/.gitkeep",
        ".env.example",
        "labs/foo/.env.example",
        "README.md",
    ]
    assert check_gitignore.violations(paths) == []


def test_generated_and_secret_paths_flagged():
    paths = [
        "labs/experiments/latest",
        "labs/experiments/runs/20260825-154147-45f/summary.json",
        "labs/experiments/internetmarke/artifacts/paid-many/python/domestic-base/checkout.json",
        "labs/experiments/internetmarke/cases/foo/stamp.png",
        "surface/artifacts/report.json",
        "surface/artifacts/structure/python/stubs/client.py",
        "surface/node_modules/typedoc/package.json",
        "test_credentials.env",
        "labs/foo/test_credentials.env",
        ".coverage",
        "foo.log",
        ".env",
        "labs/python/.env",
        ".env.local",
        ".env.production",
    ]
    bad = check_gitignore.violations(paths)
    assert len(bad) == len(paths)
