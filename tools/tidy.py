import argparse
from pathlib import Path

from split_parts import CHUNK_SIZE, split_file


REPO_ROOT = Path(__file__).resolve().parent.parent
SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    ".ipynb_checkpoints",
}


def should_skip_path(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_DIR_NAMES or part.endswith(".parts"):
            return True
    return False


def find_large_files(root: Path, chunk_size: int) -> list[Path]:
    large_files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if should_skip_path(path):
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Tidy the repository by finding large files and splitting them into "
            ".parts folders, while skipping .git, .venv, and existing split artifacts."
        )
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

    candidates = find_large_files(REPO_ROOT, CHUNK_SIZE)
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
