import argparse
import json
from pathlib import Path

CHUNK_SIZE = 30 * 1024 * 1024  # 30 MiB


def split_file(file_path: Path, chunk_size: int) -> None:
    file_size = file_path.stat().st_size
    if file_size <= chunk_size:
        return

    part_dir = file_path.parent / f"{file_path.name}.parts"
    part_dir.mkdir(exist_ok=True)

    print(f"Splitting: {file_path} ({file_size / 1024 / 1024:.2f} MB)")

    part_num = 1
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break

            part_path = part_dir / f"{file_path.name}.part{part_num:03d}"
            with open(part_path, "wb") as pf:
                pf.write(chunk)

            part_num += 1

    part_count = part_num - 1

    manifest = {
        "original_name": file_path.name,
        "original_size": file_size,
        "chunk_size": chunk_size,
        "part_count": part_count,
        "part_name_pattern": f"{file_path.name}.partNNN",
    }
    (part_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    file_path.unlink()
    print(f"Removed original: {file_path}")


def walk_and_split(target_folder: str, chunk_size: int) -> None:
    target = Path(target_folder)
    if not target.exists():
        raise FileNotFoundError(f"Target folder not found: {target}")
    if not target.is_dir():
        raise NotADirectoryError(f"Target path is not a folder: {target}")

    for path in target.rglob("*"):
        if path.is_file():
            if ".parts" in path.parts:
                continue
            split_file(path, chunk_size)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Recursively split files larger than 30 MiB into parts folders."
    )
    parser.add_argument("target_folder", help="Folder to scan recursively")
    args = parser.parse_args()

    walk_and_split(args.target_folder, CHUNK_SIZE)
    print("Done splitting.")
