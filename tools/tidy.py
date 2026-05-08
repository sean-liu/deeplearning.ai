import argparse
import os
import shutil
import subprocess
from pathlib import Path

from split_parts import CHUNK_SIZE, split_file


REPO_ROOT = Path(__file__).resolve().parent.parent
SKIP_DIR_NAMES = {
    ".git",
    ".venv",
}


def normalize_target(raw_target: str | None) -> Path:
    if raw_target is None:
        return REPO_ROOT

    target = (REPO_ROOT / raw_target).resolve()
    if REPO_ROOT not in {target, *target.parents}:
        raise ValueError(f"Target folder must stay inside the repository: {target}")
    if not target.exists():
        raise FileNotFoundError(f"Target folder not found: {target}")
    if not target.is_dir():
        raise NotADirectoryError(f"Target path is not a folder: {target}")
    return target


def is_hardcoded_skip_dir(path: Path) -> bool:
    return path.name in SKIP_DIR_NAMES or path.name.endswith(".parts")


def repo_relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def git_ignored_paths(paths: list[Path]) -> set[Path]:
    if not paths:
        return set()

    relative_paths = [repo_relative(path) for path in paths]
    result = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        input="\n".join(relative_paths) + "\n",
        text=True,
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
    )

    ignored = set()
    for line in result.stdout.splitlines():
        if line:
            ignored.add(REPO_ROOT / line)
    return ignored


def remove_pycache_dirs(root: Path) -> int:
    removed = 0
    for current_root, dirnames, _ in os_walk(root):
        current_path = Path(current_root)

        pruned_dirnames = []
        for dirname in dirnames:
            dir_path = current_path / dirname
            if is_hardcoded_skip_dir(dir_path):
                continue
            pruned_dirnames.append(dirname)
        dirnames[:] = pruned_dirnames

        git_ignored_dirs = git_ignored_paths([current_path / dirname for dirname in dirnames])
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if (current_path / dirname) not in git_ignored_dirs
        ]

        pycache_dirs = [Path(current_root, name) for name in dirnames if name == "__pycache__"]
        for pycache_dir in pycache_dirs:
            shutil.rmtree(pycache_dir)
            dirnames.remove(pycache_dir.name)
            removed += 1
    return removed


def os_walk(root: Path):
    return os.walk(root, topdown=True)


def find_large_files(root: Path, chunk_size: int) -> list[Path]:
    large_files = []
    for current_root, dirnames, filenames in os_walk(root):
        current_path = Path(current_root)

        pruned_dirnames = []
        for dirname in dirnames:
            dir_path = current_path / dirname
            if is_hardcoded_skip_dir(dir_path):
                continue
            pruned_dirnames.append(dirname)
        dirnames[:] = pruned_dirnames

        git_ignored_dirs = git_ignored_paths([current_path / dirname for dirname in dirnames])
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if (current_path / dirname) not in git_ignored_dirs
        ]

        file_paths = [current_path / filename for filename in filenames]
        git_ignored_files = git_ignored_paths(file_paths)
        for path in file_paths:
            if path in git_ignored_files:
                continue
            if path.stat().st_size > chunk_size:
                large_files.append(path)
    return sorted(large_files)


def format_size_in_mib(path: Path) -> str:
    return f"{path.stat().st_size / 1024 / 1024:.2f} MiB"


def print_candidates(files: list[Path]) -> None:
    if not files:
        print("No files larger than 30 MiB were found outside ignored folders.")
        return

    print("Files that can be split:\n")
    for path in files:
        print(f"- {path.relative_to(REPO_ROOT)} ({format_size_in_mib(path)})")


def confirm_split(files: list[Path]) -> bool:
    if not files:
        return False

    while True:
        choice = input("\nSplit these files into .parts folders? [y/N]: ").strip().lower()
        if choice in {"y", "yes"}:
            return True
        if choice in {"", "n", "no"}:
            return False
        print("Please enter 'y' or 'n'.")


def split_candidates(files: list[Path], chunk_size: int) -> None:
    for path in files:
        split_file(path, chunk_size)


def format_removed_pycache_message(count: int) -> str:
    suffix = "directory" if count == 1 else "directories"
    return f"Removed {count} __pycache__ {suffix}."


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Tidy a repo folder by cleaning __pycache__ directories and finding "
            "large files to split into .parts folders while respecting git-ignore rules."
        )
    )
    parser.add_argument(
        "target_folder",
        nargs="?",
        help="Optional folder to tidy. Defaults to the repository root.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List large-file candidates and exit without splitting.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Split candidates without asking for confirmation.",
    )
    args = parser.parse_args()

    target = normalize_target(args.target_folder)
    removed_pycache_dirs = remove_pycache_dirs(target)
    if removed_pycache_dirs:
        print(format_removed_pycache_message(removed_pycache_dirs))

    candidates = find_large_files(target, CHUNK_SIZE)
    print_candidates(candidates)

    if args.list or not candidates:
        return

    if not args.yes and not confirm_split(candidates):
        print("No files were split.")
        return

    split_candidates(candidates, CHUNK_SIZE)
    print("\nTidy complete.")


if __name__ == "__main__":
    main()
