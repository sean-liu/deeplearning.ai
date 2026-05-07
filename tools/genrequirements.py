import argparse
import ast
import json
import sys
from importlib import metadata
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    ".ipynb_checkpoints",
}
KNOWN_NON_PIP_MODULES = {
    "grader_support",
    "solutions",
}
IMPORT_TO_PACKAGE = {
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "keras": "tensorflow",
    "sklearn": "scikit-learn",
    "yaml": "PyYAML",
}


def should_skip_path(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES or part.endswith(".parts") for part in path.parts)


def iter_source_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if should_skip_path(path) or not path.is_file():
            continue
        if path.suffix in {".py", ".ipynb"}:
            files.append(path)
    return sorted(files)


def find_local_modules(root: Path) -> set[str]:
    local_modules = set()
    for path in root.rglob("*.py"):
        if should_skip_path(path):
            continue
        if path.name == "__init__.py":
            continue
        local_modules.add(path.stem)
    return local_modules


def sanitize_python_source(source: str) -> str:
    cleaned_lines = []
    for line in source.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("!", "%", "?")):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def extract_modules_from_python(source: str) -> set[str]:
    try:
        tree = ast.parse(sanitize_python_source(source))
    except SyntaxError:
        return set()

    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0 or node.module is None:
                continue
            modules.add(node.module.split(".", 1)[0])
    return modules


def extract_modules_from_notebook(path: Path) -> set[str]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    modules = set()
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        modules.update(extract_modules_from_python(source))
    return modules


def collect_imported_modules(root: Path) -> set[str]:
    modules = set()
    for path in iter_source_files(root):
        if path.suffix == ".py":
            modules.update(extract_modules_from_python(path.read_text(encoding="utf-8")))
        else:
            modules.update(extract_modules_from_notebook(path))
    return modules


def build_distribution_index() -> dict[str, str]:
    package_index = {}
    for import_name, distributions in metadata.packages_distributions().items():
        if not distributions:
            continue
        package_index[import_name] = sorted(distributions)[0]
    return package_index


def resolve_requirements(
    modules: set[str], local_modules: set[str], distribution_index: dict[str, str]
) -> tuple[list[str], list[str]]:
    stdlib_modules = set(getattr(sys, "stdlib_module_names", set()))
    requirements = set()
    unresolved = set()

    for module in sorted(modules):
        if module in stdlib_modules:
            continue
        if module in local_modules:
            continue
        if module in KNOWN_NON_PIP_MODULES:
            continue

        package_name = (
            IMPORT_TO_PACKAGE.get(module)
            or distribution_index.get(module)
            or module
        )
        if package_name:
            requirements.add(package_name)
        else:
            unresolved.add(module)

    return sorted(requirements, key=str.casefold), sorted(unresolved, key=str.casefold)


def normalize_target(raw_target: str) -> Path:
    target = (REPO_ROOT / raw_target).resolve()
    if not target.exists():
        raise FileNotFoundError(f"Target folder not found: {target}")
    if not target.is_dir():
        raise NotADirectoryError(f"Target path is not a folder: {target}")
    return target


def write_requirements_file(
    requirements_path: Path, requirements: list[str], force: bool
) -> None:
    if requirements_path.exists() and not force:
        raise FileExistsError(
            f"requirements.txt already exists: {requirements_path}\n"
            "Use --force if you want to replace it."
        )

    content = "\n".join(requirements)
    if content:
        content += "\n"
    requirements_path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Scan a target folder for Python and notebook imports and create a "
            "requirements.txt file when one is missing."
        )
    )
    parser.add_argument("target_folder", help="Folder to scan recursively")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing requirements.txt file.",
    )
    args = parser.parse_args()

    target = normalize_target(args.target_folder)
    requirements_path = target / "requirements.txt"
    local_modules = find_local_modules(target)
    modules = collect_imported_modules(target)
    distribution_index = build_distribution_index()
    requirements, unresolved = resolve_requirements(
        modules, local_modules, distribution_index
    )

    write_requirements_file(requirements_path, requirements, args.force)

    print(f"Wrote requirements file: {requirements_path}")
    if requirements:
        print("\nResolved packages:")
        for requirement in requirements:
            print(f"- {requirement}")
    else:
        print("\nNo third-party packages were resolved.")

    if unresolved:
        print("\nSkipped unresolved imports (review manually if needed):")
        for module in unresolved:
            print(f"- {module}")


if __name__ == "__main__":
    main()
