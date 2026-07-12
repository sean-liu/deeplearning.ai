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


def normalize_restore_root(raw_value: str) -> Path:
    candidate = Path(raw_value).expanduser()
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate

    try:
        candidate = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ValueError(f"folder does not exist: {raw_value}") from error

    if not candidate.is_dir():
        raise ValueError(f"folder is not a directory: {candidate}")
    if not candidate.is_relative_to(REPO_ROOT):
        raise ValueError(f"folder must be inside the repository: {candidate}")
    return candidate


def validate_legacy_parts_manifest(parts_path: Path) -> str:
    if parts_path.is_symlink() or not parts_path.is_dir():
        raise ValueError("parts path must be a real directory, not a symbolic link")

    manifest_path = parts_path / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("manifest.json must be a real file")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read manifest.json: {error}") from error
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")

    original_name = manifest.get("original_name")
    if (
        not isinstance(original_name, str)
        or not original_name
        or original_name in {".", ".."}
        or "/" in original_name
        or "\\" in original_name
        or Path(original_name).name != original_name
    ):
        raise ValueError("original_name must be a single safe filename")
    if parts_path.name != f"{original_name}.parts":
        raise ValueError("parts directory name does not match original_name")

    expected_size = manifest.get("original_size")
    expected_count = manifest.get("part_count")
    if (
        not isinstance(expected_size, int)
        or isinstance(expected_size, bool)
        or expected_size < 0
    ):
        raise ValueError("original_size must be a non-negative integer")
    if (
        not isinstance(expected_count, int)
        or isinstance(expected_count, bool)
        or expected_count < 1
    ):
        raise ValueError("part_count must be a positive integer")

    expected_names = {
        f"{original_name}.part{index:03d}"
        for index in range(1, expected_count + 1)
    }
    try:
        actual_entries = {path.name: path for path in parts_path.iterdir()}
    except OSError as error:
        raise ValueError(f"could not inspect parts directory: {error}") from error
    actual_part_names = set(actual_entries) - {"manifest.json"}
    missing = sorted(expected_names - actual_part_names)
    extra = sorted(actual_part_names - expected_names)
    if missing:
        raise ValueError(f"missing expected part(s): {', '.join(missing)}")
    if extra:
        raise ValueError(f"unexpected extra part(s): {', '.join(extra)}")

    expected_parts = [
        actual_entries[f"{original_name}.part{index:03d}"]
        for index in range(1, expected_count + 1)
    ]
    invalid_parts = [
        path.name for path in expected_parts if path.is_symlink() or not path.is_file()
    ]
    if invalid_parts:
        raise ValueError(
            f"part(s) must be real files: {', '.join(sorted(invalid_parts))}"
        )
    return original_name


def write_legacy_archive_marker(marker_path: Path, archive_name: str) -> None:
    directory_name = archive_name.removesuffix(".zip")
    if not directory_name:
        raise ValueError("ZIP archive name must include a non-empty directory name")

    marker = {
        "format_version": ARCHIVE_FORMAT_VERSION,
        "archive_name": archive_name,
        "directory_name": directory_name,
    }
    temporary_marker = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=marker_path.parent,
            prefix=f".{marker_path.name}.",
            delete=False,
        ) as marker_file:
            json.dump(marker, marker_file, indent=2)
            marker_file.write("\n")
            temporary_marker = Path(marker_file.name)
        temporary_marker.replace(marker_path)
    finally:
        if temporary_marker is not None:
            temporary_marker.unlink(missing_ok=True)


def restore_legacy_parts(root: Path) -> bool:
    candidates = sorted(path for path in root.rglob("*.parts") if path.is_dir())
    unmarked_candidates = []
    for parts_path in candidates:
        archive_name = parts_path.name.removesuffix(".parts")
        marker_path = parts_path.parent / f"{archive_name}.archive.json"
        if marker_path.exists() or marker_path.is_symlink():
            continue
        unmarked_candidates.append(parts_path)

    if not unmarked_candidates:
        print(f"No unmarked legacy parts folders found under: {root}")
        return True

    print(
        f"Found {len(unmarked_candidates)} unmarked legacy parts folder(s) under: {root}"
    )
    all_succeeded = True
    for parts_path in unmarked_candidates:
        try:
            original_name = validate_legacy_parts_manifest(parts_path)
            output_path = parts_path.parent / original_name
            if output_path.exists() or output_path.is_symlink():
                raise ValueError(f"restore destination already exists: {output_path}")

            if not original_name.endswith(".zip"):
                merge_parts_dir(parts_path)
                print(f"Restored legacy file: {output_path}")
                continue

            directory_name = original_name.removesuffix(".zip")
            target_directory = parts_path.parent / directory_name
            if target_directory.exists() or target_directory.is_symlink():
                raise ValueError(
                    f"ZIP restore destination already exists: {target_directory}"
                )

            marker_path = parts_path.parent / f"{original_name}.archive.json"
            write_legacy_archive_marker(marker_path, original_name)
            try:
                merge_parts_dir(parts_path)
            except (OSError, RuntimeError, ValueError, KeyError):
                marker_path.unlink(missing_ok=True)
                raise

            if not restore_tidy_archive(marker_path):
                all_succeeded = False
        except (OSError, RuntimeError, ValueError, KeyError) as error:
            all_succeeded = False
            print(f"Could not restore legacy parts {parts_path}: {error}")

    return all_succeeded


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


def restore_tidy_archive(marker_path: Path) -> bool:
    try:
        archive_path, target_directory, directory_name = validate_archive_marker(marker_path)
    except ValueError as error:
        print(f"Skipping invalid tidy archive marker {marker_path}: {error}")
        return False

    parts_path = archive_path.with_name(f"{archive_path.name}.parts")
    if parts_path.exists():
        print(f"Skipping archive restore until parts are merged: {parts_path}")
        return False
    if not archive_path.is_file():
        print(f"Skipping archive restore; archive file is missing: {archive_path}")
        return False
    if target_directory.exists() or target_directory.is_symlink():
        print(
            f"Skipping archive restore; destination already exists: {target_directory}"
        )
        return False

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
        return True
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile) as error:
        print(f"Could not restore tidy archive {archive_path}: {error}")
        return False
    finally:
        if temporary_root is not None:
            shutil.rmtree(temporary_root, ignore_errors=True)


def restore_tidy_archives(root: Path) -> None:
    for marker_path in find_archive_markers(root):
        restore_tidy_archive(marker_path)


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
    parser.add_argument(
        "--restore-legacy-parts",
        metavar="FOLDER",
        help=(
            "Only restore unmarked legacy *.parts folders recursively under an "
            "existing repository folder, then exit."
        ),
    )
    args = parser.parse_args()

    if args.restore_legacy_parts is not None:
        if args.assignment or args.list:
            parser.error(
                "--restore-legacy-parts cannot be combined with an assignment or --list"
            )
        try:
            restore_root = normalize_restore_root(args.restore_legacy_parts)
        except ValueError as error:
            parser.error(str(error))
        if not restore_legacy_parts(restore_root):
            raise SystemExit(1)
        print("Legacy parts restore complete.")
        return

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
