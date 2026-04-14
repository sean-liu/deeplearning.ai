import argparse
import subprocess
import sys
from pathlib import Path

from mergeparts import walk_and_merge


REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = REPO_ROOT / ".venv"


def find_parts_dirs(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.parts") if path.is_dir())


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
    parts_dirs = find_parts_dirs(root)
    if not parts_dirs:
        print("No split file folders found. Skipping merge step.")
        return

    print(f"Found {len(parts_dirs)} split file folder(s). Reconstructing files...")
    walk_and_merge(str(root))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare the repository for a chosen assignment by merging split files, "
            "creating a repo-level virtual environment, and installing dependencies."
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

    prepare_split_files(REPO_ROOT)
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
