import os
import re
import tempfile
import zipfile
from pathlib import Path

DOWNLOAD_ALL_LABS = True
EXPORT_COMMENT = b"deeplearning.ai/tools/download.py"
LAB_ZIP, WORKSPACE_ZIP = "lab.zip", "course_labs.zip"


def workspace_root(cwd):
    override = os.environ.get("LAB_WORKSPACE_ROOT")
    selected = (cwd / Path(override).expanduser()).resolve(strict=True) if override else None
    home = Path.home().resolve()
    for candidate in (cwd, *cwd.parents):
        git = candidate / ".git"
        if candidate in (home, candidate.parent) or git.exists() or git.is_symlink():
            break
        if selected == candidate:
            return candidate
        marker = candidate / ".lab-workspace-root"
        if selected is None and not marker.is_symlink() and marker.is_file():
            return candidate
    if selected is not None or candidate == cwd:
        raise ValueError("Workspace root must be at or above the current directory, "
                         "below any home, system root, or Git checkout boundary.")
    print(f"Workspace root not identified. Exporting only {cwd}. Set LAB_WORKSPACE_ROOT to override.")
    return cwd


def visible(path):
    return not path.name.startswith(".") and not path.is_symlink()


def is_export(path, *, legacy=False):
    if path.suffix.lower() != ".zip":
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.comment == EXPORT_COMMENT or (
                legacy and path.name in (LAB_ZIP, WORKSPACE_ZIP))
    except zipfile.BadZipFile:
        return False


def raise_walk_error(error):
    raise error


def write_archive(root, output):
    if output.is_symlink() or (output.exists() and not (output.is_file() and is_export(output))):
        raise FileExistsError(f"Move the existing file or directory before exporting: {output}")

    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".download-") as scratch:
        temporary = Path(scratch) / "export.zip"
        temporary.touch(mode=0o600)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.comment = EXPORT_COMMENT
            for directory, dirs, files in os.walk(root, onerror=raise_walk_error):
                directory = Path(directory)
                dirs[:] = [name for name in dirs if visible(directory / name)]
                for name in files:
                    path = directory / name
                    if path == output or not visible(path) or not path.is_file():
                        continue
                    if not is_export(path, legacy=True):
                        archive.write(path, path.relative_to(root))
        temporary.replace(output)


def main():
    cwd = Path.cwd().resolve()
    root = workspace_root(cwd) if DOWNLOAD_ALL_LABS else cwd
    name = WORKSPACE_ZIP if DOWNLOAD_ALL_LABS else LAB_ZIP
    folders = [path.name for path in root.iterdir() if visible(path) and path.is_dir()]
    if len(folders) == 1 and not re.search(r'[<>:"/\\|?*\x00-\x1f]', folders[0]):
        name = f"{folders[0]}.zip"
    output = cwd / name
    write_archive(root, output)
    print(f"Created ZIP file: {output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from None
