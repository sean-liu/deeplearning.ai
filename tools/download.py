import os
import re
import tempfile
import zipfile
from pathlib import Path

DOWNLOAD_ALL_LABS = True
ROOT_ENV = "LAB_WORKSPACE_ROOT"
ROOT_MARKER = ".lab-workspace-root"
LEGACY_EXPORT_NAMES = {"course_labs.zip", "lab.zip"}
EXPORT_COMMENT = b"deeplearning.ai/tools/download.py"


def workspace_ancestors(current_dir):
    home = Path.home().resolve()
    for candidate in (current_dir, *current_dir.parents):
        git_marker = candidate / ".git"
        if (
            candidate == candidate.parent or candidate == home
            or git_marker.exists() or git_marker.is_symlink()
        ):
            break
        yield candidate


def workspace_root(current_dir):
    candidates = tuple(workspace_ancestors(current_dir))
    if not candidates:
        raise ValueError(f"Refusing to export a home, system root, or Git checkout: {current_dir}")

    override = os.environ.get(ROOT_ENV)
    if override:
        root = (current_dir / Path(override).expanduser()).resolve(strict=True)
        if root not in candidates:
            raise ValueError(
                f"{ROOT_ENV} must name the current directory or an ancestor below "
                "any home, system, or Git checkout boundary"
            )
        return root

    for candidate in candidates:
        marker = candidate / ROOT_MARKER
        if not marker.is_symlink() and marker.is_file():
            return candidate
    print(
        f"Workspace root not identified. Exporting only {current_dir}. "
        f"Set {ROOT_ENV} to export the whole workspace."
    )
    return current_dir


def visible_subdirectory(path):
    return not path.name.startswith(".") and not path.is_symlink() and path.is_dir()


def archive_name(root, default_name):
    folder_names = [path.name for path in root.iterdir() if visible_subdirectory(path)]
    if len(folder_names) == 1:
        name = folder_names[0]
        if not re.search(r'[<>:"/\\|?*\x00-\x1f]', name):
            return f"{name}.zip"
    return default_name


def is_export(path, *, include_legacy=False):
    if path.suffix.lower() != ".zip":
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.comment == EXPORT_COMMENT or (
                include_legacy and path.name in LEGACY_EXPORT_NAMES
            )
    except zipfile.BadZipFile:
        return False


def write_archive(root, output):
    if output.is_symlink() or (
        output.exists() and not (output.is_file() and is_export(output))
    ):
        raise FileExistsError(f"Move the existing file or directory before exporting: {output}")

    # A failed export must leave any previous archive intact.
    with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".download-", delete=False) as file:
        temporary = Path(file.name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.comment = EXPORT_COMMENT
            for directory, dirs, files in os.walk(root, followlinks=False, onerror=raise_walk_error):
                directory = Path(directory)
                dirs[:] = [name for name in dirs if visible_subdirectory(directory / name)]
                for name in files:
                    path = directory / name
                    if (
                        name.startswith(".") or path == output or path.is_symlink()
                        or not path.is_file() or is_export(path, include_legacy=True)
                    ):
                        continue
                    archive.write(path, path.relative_to(root))
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()


def raise_walk_error(error):
    raise error


def main():
    current_dir = Path.cwd().resolve()
    root = workspace_root(current_dir) if DOWNLOAD_ALL_LABS else current_dir
    default_name = "course_labs.zip" if DOWNLOAD_ALL_LABS else "lab.zip"
    output = current_dir / archive_name(root, default_name)
    write_archive(root, output)
    print(f"Created ZIP file: {output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from None
