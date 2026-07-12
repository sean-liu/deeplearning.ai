import argparse
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from split_parts import CHUNK_SIZE, split_file


REPO_ROOT = Path(__file__).resolve().parent.parent
SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
}
DIRECT_FILE_LIMIT = 200
ARCHIVE_FORMAT_VERSION = 1


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

    if any(REPO_ROOT not in {path, *path.parents} for path in paths):
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

        pycache_dirs = [Path(current_root, name) for name in dirnames if name == "__pycache__"]
        for pycache_dir in pycache_dirs:
            shutil.rmtree(pycache_dir)
            dirnames.remove(pycache_dir.name)
            removed += 1

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
    return removed


def os_walk(root: Path):
    return os.walk(root, topdown=True)


def filtered_walk(root: Path):
    for current_root, dirnames, filenames in os_walk(root):
        current_path = Path(current_root)

        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not is_hardcoded_skip_dir(current_path / dirname)
            and not (current_path / dirname).is_symlink()
        ]
        git_ignored_dirs = git_ignored_paths([current_path / dirname for dirname in dirnames])
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if (current_path / dirname) not in git_ignored_dirs
        ]

        file_paths = [current_path / filename for filename in filenames]
        git_ignored_files = git_ignored_paths(file_paths)
        regular_files = [
            path
            for path in file_paths
            if path not in git_ignored_files and path.is_file() and not path.is_symlink()
        ]
        yield current_path, dirnames, regular_files


def find_large_files(root: Path, chunk_size: int) -> list[Path]:
    large_files = []
    for _, _, regular_files in filtered_walk(root):
        for path in regular_files:
            if path.stat().st_size > chunk_size:
                large_files.append(path)
    return sorted(large_files)


def find_archive_directories(root: Path) -> list[Path]:
    candidates = []
    for current_path, _, regular_files in filtered_walk(root):
        if len(regular_files) > DIRECT_FILE_LIMIT:
            candidates.append(current_path)

    # Archiving an ancestor includes all of its descendants, so do not offer
    # overlapping archive operations that could invalidate one another.
    return [
        path for path in candidates if not any(parent in candidates for parent in path.parents)
    ]


def format_size_in_mib(path: Path) -> str:
    return f"{path.stat().st_size / 1024 / 1024:.2f} MiB"


def print_candidates(files: list[Path], directories: list[Path]) -> None:
    if not files and not directories:
        print("No large-file or high-file-count directory candidates were found outside ignored folders.")
        return

    if files:
        print("Files that can be split:\n")
        for path in files:
            print(f"- {path.relative_to(REPO_ROOT)} ({format_size_in_mib(path)})")

    if directories:
        if files:
            print()
        print(f"Directories with more than {DIRECT_FILE_LIMIT} direct regular files that can be archived:\n")
        for path in directories:
            print(f"- {path.relative_to(REPO_ROOT)}")


def confirm_tidy(files: list[Path], directories: list[Path]) -> bool:
    if not files and not directories:
        return False

    while True:
        choice = input(
            "\nSplit the listed large files and archive the listed directories? [y/N]: "
        ).strip().lower()
        if choice in {"y", "yes"}:
            return True
        if choice in {"", "n", "no"}:
            return False
        print("Please enter 'y' or 'n'.")


def split_candidates(files: list[Path], chunk_size: int) -> None:
    for path in files:
        split_file(path, chunk_size)


def archive_directory(directory: Path, chunk_size: int) -> None:
    archive_path = directory.parent / f"{directory.name}.zip"
    marker_path = directory.parent / f"{archive_path.name}.archive.json"
    parts_path = directory.parent / f"{archive_path.name}.parts"
    conflicts = [
        path
        for path in (archive_path, marker_path, parts_path)
        if path.exists() or path.is_symlink()
    ]
    if conflicts:
        print(
            f"Skipping archive for {directory}: destination already exists: "
            + ", ".join(str(path) for path in conflicts)
        )
        return

    with tempfile.NamedTemporaryFile(
        dir=directory.parent, prefix=f".{archive_path.name}.", suffix=".tmp", delete=False
    ) as temp_file:
        temp_archive = Path(temp_file.name)

    try:
        with zipfile.ZipFile(temp_archive, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(f"{directory.name}/", "")
            for current_path, dirnames, regular_files in filtered_walk(directory):
                relative_directory = current_path.relative_to(directory.parent).as_posix()
                for dirname in sorted(dirnames):
                    archive.writestr(f"{relative_directory}/{dirname}/", "")
                for source_path in sorted(regular_files):
                    archive.write(
                        source_path,
                        source_path.relative_to(directory.parent).as_posix(),
                    )

        with zipfile.ZipFile(temp_archive) as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                raise RuntimeError(f"ZIP integrity check failed at member: {bad_member}")

        os.link(temp_archive, archive_path)
        with marker_path.open("x", encoding="utf-8") as marker_file:
            json.dump(
                {
                    "format_version": ARCHIVE_FORMAT_VERSION,
                    "archive_name": archive_path.name,
                    "directory_name": directory.name,
                },
                marker_file,
                indent=2,
            )
            marker_file.write("\n")
        shutil.rmtree(directory)
        print(f"Archived: {directory} -> {archive_path}")

        if archive_path.stat().st_size > chunk_size:
            split_file(archive_path, chunk_size)
    except Exception as error:
        print(f"Could not archive {directory}: {error}")
    finally:
        temp_archive.unlink(missing_ok=True)


def format_removed_pycache_message(count: int) -> str:
    suffix = "directory" if count == 1 else "directories"
    return f"Removed {count} __pycache__ {suffix}."


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Tidy a repo folder by cleaning __pycache__ directories and finding "
            "large files to split and high-file-count directories to archive while "
            "respecting git-ignore rules."
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
        help="List large-file and directory-archive candidates and exit without changing them.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Process large-file and directory-archive candidates without asking for confirmation.",
    )
    args = parser.parse_args()

    target = normalize_target(args.target_folder)
    removed_pycache_dirs = remove_pycache_dirs(target)
    if removed_pycache_dirs:
        print(format_removed_pycache_message(removed_pycache_dirs))

    archive_directories = find_archive_directories(target)
    candidates = [
        path
        for path in find_large_files(target, CHUNK_SIZE)
        if not any(directory in path.parents for directory in archive_directories)
    ]
    print_candidates(candidates, archive_directories)

    if args.list or (not candidates and not archive_directories):
        return

    if not args.yes and not confirm_tidy(candidates, archive_directories):
        print("No candidates were processed.")
        return

    split_candidates(candidates, CHUNK_SIZE)
    for directory in archive_directories:
        archive_directory(directory, CHUNK_SIZE)
    print("\nTidy complete.")


if __name__ == "__main__":
    main()
