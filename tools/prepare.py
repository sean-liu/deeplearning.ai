import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from pathlib import PurePosixPath

from merge_parts import merge_parts_dir


REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = REPO_ROOT / ".venv"
ARCHIVE_FORMAT_VERSION = 1


def find_archive_markers(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.zip.archive.json") if path.is_file())


def validate_archive_marker(marker_path: Path) -> tuple[Path, Path, str]:
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read JSON: {error}") from error

    if not isinstance(marker, dict) or marker.get("format_version") != ARCHIVE_FORMAT_VERSION:
        raise ValueError("unsupported or missing archive format version")

    archive_name = marker.get("archive_name")
    directory_name = marker.get("directory_name")
    for label, value in (("archive_name", archive_name), ("directory_name", directory_name)):
        if (
            not isinstance(value, str)
            or not value
            or value in {".", ".."}
            or "/" in value
            or "\\" in value
            or Path(value).name != value
        ):
            raise ValueError(f"invalid {label}")

    if archive_name != f"{directory_name}.zip":
        raise ValueError("archive_name must be the directory name followed by .zip")
    if marker_path.name != f"{archive_name}.archive.json":
        raise ValueError("marker filename does not match archive_name")

    return marker_path.parent / archive_name, marker_path.parent / directory_name, directory_name


def find_assignment_requirements(root: Path) -> list[Path]:
    return sorted(root.glob("deep_learning_specialization/**/requirements.txt"))


def normalize_assignment_path(raw_value: str) -> Path:
    candidate = (REPO_ROOT / raw_value).resolve()

    if candidate.is_file():
        if candidate.name != "requirements.txt":
            raise FileNotFoundError(
                f"Expected a requirements.txt file, got: {candidate}"
            )
        return candidate

    requirements_path = candidate / "requirements.txt"
    if requirements_path.exists():
        return requirements_path

    raise FileNotFoundError(
        f"Could not find requirements.txt for assignment path: {raw_value}"
    )


def choose_assignment_interactively(requirement_files: list[Path]) -> Path:
    print("Available assignments:\n")
    for index, requirement_file in enumerate(requirement_files, start=1):
        print(f"{index:2d}. {requirement_file.parent.relative_to(REPO_ROOT)}")

    while True:
        choice = input("\nEnter the assignment number to prepare: ").strip()
        if not choice.isdigit():
            print("Please enter a number from the list.")
            continue

        selected_index = int(choice)
        if 1 <= selected_index <= len(requirement_files):
            return requirement_files[selected_index - 1]

        print("Selection out of range. Try again.")


def ensure_repo_venv() -> Path:
    venv_python = VENV_DIR / "bin" / "python"
    if venv_python.exists():
        print(f"Using existing virtual environment: {VENV_DIR}")
        return venv_python

    print(f"Creating virtual environment: {VENV_DIR}")
    subprocess.run(
        [sys.executable, "-m", "venv", str(VENV_DIR)],
        check=True,
        cwd=REPO_ROOT,
    )
    return venv_python


def install_requirements(venv_python: Path, requirements_path: Path) -> None:
    print(f"Installing dependencies from: {requirements_path.relative_to(REPO_ROOT)}")
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-r", str(requirements_path)],
        check=True,
        cwd=REPO_ROOT,
    )


def ensure_ipykernel(venv_python: Path) -> None:
    check_command = [
        str(venv_python),
        "-c",
        "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('ipykernel') else 1)",
    ]
    result = subprocess.run(check_command, cwd=REPO_ROOT, check=False)

    if result.returncode == 0:
        print("ipykernel is already installed in the repo virtual environment.")
        return

    print("Installing ipykernel for VS Code and Jupyter support...")
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "ipykernel"],
        check=True,
        cwd=REPO_ROOT,
    )


def prepare_split_files(root: Path) -> None:
    markers = find_archive_markers(root)
    parts_dirs = []
    for marker_path in markers:
        try:
            archive_path, _, _ = validate_archive_marker(marker_path)
        except ValueError as error:
            print(f"Skipping invalid tidy archive marker {marker_path}: {error}")
            continue
        parts_path = archive_path.with_name(f"{archive_path.name}.parts")
        if parts_path.exists():
            parts_dirs.append((archive_path, parts_path))

    if not parts_dirs:
        print("No tidy archive parts folders found for this assignment. Skipping merge step.")
        return

    print(
        f"Found {len(parts_dirs)} tidy archive parts folder(s) for this assignment. "
        "Reconstructing archives..."
    )
    for archive_path, parts_path in parts_dirs:
        if not parts_path.is_dir():
            print(f"Skipping non-directory archive parts path: {parts_path}")
        elif archive_path.exists():
            print(
                f"Skipping {parts_path}: archive destination already exists: {archive_path}"
            )
        else:
            try:
                merge_parts_dir(parts_path)
            except (OSError, RuntimeError, ValueError, KeyError) as error:
                print(f"Could not merge tidy archive parts {parts_path}: {error}")


def validate_zip_members(archive: zipfile.ZipFile, directory_name: str) -> None:
    seen_names = set()
    prefix = f"{directory_name}/"
    for member in archive.infolist():
        name = member.filename
        if (
            not name
            or name in seen_names
            or "\\" in name
            or "//" in name
            or not name.startswith(prefix)
        ):
            raise ValueError(f"unsafe ZIP entry: {name!r}")
        seen_names.add(name)

        member_path = PurePosixPath(name)
        if member_path.is_absolute() or any(part in {".", ".."} for part in member_path.parts):
            raise ValueError(f"unsafe ZIP entry: {name!r}")
        if len(member_path.parts) == 1 and not member.is_dir():
            raise ValueError(f"archive root is not a directory: {name!r}")
        if (member.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError(f"symbolic-link ZIP entry is not allowed: {name!r}")


def restore_tidy_archives(root: Path) -> None:
    for marker_path in find_archive_markers(root):
        try:
            archive_path, target_directory, directory_name = validate_archive_marker(marker_path)
        except ValueError as error:
            print(f"Skipping invalid tidy archive marker {marker_path}: {error}")
            continue

        parts_path = archive_path.with_name(f"{archive_path.name}.parts")
        if parts_path.exists():
            print(f"Skipping archive restore until parts are merged: {parts_path}")
            continue
        if not archive_path.is_file():
            print(f"Skipping archive restore; archive file is missing: {archive_path}")
            continue
        if target_directory.exists() or target_directory.is_symlink():
            print(
                f"Skipping archive restore; destination already exists: {target_directory}"
            )
            continue

        temporary_root = None
        try:
            with zipfile.ZipFile(archive_path) as archive:
                bad_member = archive.testzip()
                if bad_member is not None:
                    raise RuntimeError(f"ZIP integrity check failed at member: {bad_member}")
                validate_zip_members(archive, directory_name)

                temporary_root = Path(
                    tempfile.mkdtemp(
                        dir=archive_path.parent,
                        prefix=f".{directory_name}.restore-",
                    )
                )
                for member in archive.infolist():
                    destination = temporary_root.joinpath(*PurePosixPath(member.filename).parts)
                    if member.is_dir():
                        destination.mkdir(parents=True, exist_ok=True)
                    else:
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(member) as source, open(destination, "wb") as output:
                            shutil.copyfileobj(source, output)

            restored_directory = temporary_root / directory_name
            if not restored_directory.is_dir():
                raise RuntimeError("archive did not restore the expected top-level directory")
            if target_directory.exists() or target_directory.is_symlink():
                raise RuntimeError(f"destination already exists: {target_directory}")

            restored_directory.rename(target_directory)
            archive_path.unlink()
            marker_path.unlink()
            print(f"Restored tidy archive: {archive_path} -> {target_directory}")
        except (OSError, RuntimeError, ValueError, zipfile.BadZipFile) as error:
            print(f"Could not restore tidy archive {archive_path}: {error}")
        finally:
            if temporary_root is not None:
                shutil.rmtree(temporary_root, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare the repository for a chosen assignment by merging and restoring "
            "tidy-marked archives, creating a repo-level virtual environment, and "
            "installing dependencies."
        )
    )
    parser.add_argument(
        "assignment",
        nargs="?",
        help=(
            "Optional assignment folder or requirements.txt path. "
            "If omitted, an interactive picker is shown."
        ),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available assignments and exit.",
    )
    args = parser.parse_args()

    requirement_files = find_assignment_requirements(REPO_ROOT)
    if not requirement_files:
        raise FileNotFoundError("No assignment requirements.txt files were found.")

    if args.list:
        for requirement_file in requirement_files:
            print(requirement_file.parent.relative_to(REPO_ROOT))
        return

    if args.assignment:
        requirements_path = normalize_assignment_path(args.assignment)
    else:
        requirements_path = choose_assignment_interactively(requirement_files)

    prepare_split_files(requirements_path.parent)
    restore_tidy_archives(requirements_path.parent)
    venv_python = ensure_repo_venv()
    install_requirements(venv_python, requirements_path)
    ensure_ipykernel(venv_python)

    print("\nPreparation complete.")
    print(f"Assignment: {requirements_path.parent.relative_to(REPO_ROOT)}")
    print(f"Virtual environment: {VENV_DIR}")
    print(f"Interpreter: {venv_python}")
    print("\nNext steps:")
    print("1. Open the notebook in VS Code.")
    print("2. Use 'Select Kernel' and choose the interpreter above.")
    print("3. If you prefer terminal work, you can still activate the environment:")
    print("   source .venv/bin/activate")


if __name__ == "__main__":
    main()
