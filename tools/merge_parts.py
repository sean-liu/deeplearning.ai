import argparse
import filecmp
import json
import shutil
import tempfile
from pathlib import Path


def load_manifest(parts_dir: Path) -> dict:
    manifest_path = parts_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_parts_dir(parts_dir: Path) -> None:
    if not parts_dir.is_dir() or not parts_dir.name.endswith(".parts"):
        return

    manifest = load_manifest(parts_dir)
    original_name = manifest["original_name"]
    expected_size = manifest["original_size"]
    expected_count = manifest["part_count"]

    output_file = parts_dir.parent / original_name

    expected_parts = [
        parts_dir / f"{original_name}.part{i:03d}"
        for i in range(1, expected_count + 1)
    ]

    missing = [str(p) for p in expected_parts if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing expected part files:\n" + "\n".join(missing)
        )

    # Detect unexpected extra part files that could cause confusion.
    actual_parts = sorted(parts_dir.glob(f"{original_name}.part*"))
    expected_set = {p.name for p in expected_parts}
    extra = [p.name for p in actual_parts if p.name not in expected_set]
    if extra:
        raise RuntimeError(
            "Unexpected extra part files found in parts folder:\n" + "\n".join(extra)
        )

    print(f"Merging: {parts_dir} -> {output_file}")

    with tempfile.NamedTemporaryFile(
        dir=parts_dir.parent, prefix=f".{original_name}.merge-", delete=False
    ) as temp_file:
        temp_output = Path(temp_file.name)

    try:
        with open(temp_output, "wb") as out:
            for part_file in expected_parts:
                with open(part_file, "rb") as pf:
                    while True:
                        chunk = pf.read(1024 * 1024)
                        if not chunk:
                            break
                        out.write(chunk)

        actual_size = temp_output.stat().st_size
        if actual_size != expected_size:
            raise RuntimeError(
                f"Size mismatch after merge for {output_file}: "
                f"expected {expected_size}, got {actual_size}"
            )

        if output_file.exists():
            if not output_file.is_file():
                raise RuntimeError(
                    f"Expected merge output path to be a file: {output_file}"
                )
            if filecmp.cmp(output_file, temp_output, shallow=False):
                print(f"Existing merged file already matches parts: {output_file}")
                temp_output.unlink(missing_ok=True)
            else:
                print(f"Existing file differs from parts. Replacing: {output_file}")
                temp_output.replace(output_file)
        else:
            temp_output.replace(output_file)
    finally:
        temp_output.unlink(missing_ok=True)

    shutil.rmtree(parts_dir)
    print(f"Removed parts folder: {parts_dir}")


def walk_and_merge(target_folder: str) -> None:
    target = Path(target_folder)
    if not target.exists():
        raise FileNotFoundError(f"Target folder not found: {target}")
    if not target.is_dir():
        raise NotADirectoryError(f"Target path is not a folder: {target}")

    parts_dirs = [p for p in target.rglob("*.parts") if p.is_dir()]
    for parts_dir in parts_dirs:
        merge_parts_dir(parts_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Recursively merge files from *.parts folders."
    )
    parser.add_argument("target_folder", help="Folder to scan recursively")
    args = parser.parse_args()

    walk_and_merge(args.target_folder)
    print("Done merging.")
