from __future__ import annotations

import subprocess


def get_changed_files(base_ref: str, head_ref: str) -> list[tuple[str, str]]:
    """Return list of (file_path, status) for changed Python files between refs.

    Status is A (added), M (modified), D (deleted), or R (renamed).
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-status", "--diff-filter=ADMR", base_ref, head_ref],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return []

    files = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0][0]
        fpath = parts[-1]
        if fpath.endswith(".py"):
            files.append((fpath, status))
    return files


def get_file_at_ref(ref: str, file_path: str) -> str | None:
    """Get file contents at a given git ref."""
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{file_path}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return None
