import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools import prepare


def make_parts(root: Path, original_name: str, content: bytes) -> Path:
    parts_path = root / f"{original_name}.parts"
    parts_path.mkdir()
    chunks = (content[: max(1, len(content) // 2)], content[max(1, len(content) // 2) :])
    chunks = tuple(chunk for chunk in chunks if chunk)
    for index, chunk in enumerate(chunks, start=1):
        (parts_path / f"{original_name}.part{index:03d}").write_bytes(chunk)
    (parts_path / "manifest.json").write_text(
        json.dumps(
            {
                "original_name": original_name,
                "original_size": len(content),
                "part_count": len(chunks),
            }
        ),
        encoding="utf-8",
    )
    return parts_path


def zip_content(directory_name: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{directory_name}/", "")
        archive.writestr(f"{directory_name}/item.txt", "restored")
    return buffer.getvalue()


class LegacyPartsMarkingTests(unittest.TestCase):
    def test_marking_is_non_destructive_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            plain_parts = make_parts(root, "notes.bin", b"plain legacy content")
            archive_parts = make_parts(root, "images.zip", zip_content("images"))
            before = {
                path.relative_to(root): path.read_bytes()
                for parts_path in (plain_parts, archive_parts)
                for path in parts_path.iterdir()
            }

            self.assertTrue(prepare.mark_legacy_parts(root))

            plain_marker = root / "notes.bin.parts.prepare.json"
            archive_marker = root / "images.zip.archive.json"
            self.assertEqual(
                json.loads(plain_marker.read_text(encoding="utf-8")),
                {
                    "format_version": 1,
                    "parts_directory_name": "notes.bin.parts",
                    "original_name": "notes.bin",
                },
            )
            self.assertEqual(
                json.loads(archive_marker.read_text(encoding="utf-8")),
                {
                    "format_version": 1,
                    "archive_name": "images.zip",
                    "directory_name": "images",
                },
            )
            self.assertFalse((root / "notes.bin").exists())
            self.assertFalse((root / "images.zip").exists())
            self.assertFalse((root / "images").exists())
            self.assertEqual(
                {
                    path.relative_to(root): path.read_bytes()
                    for parts_path in (plain_parts, archive_parts)
                    for path in parts_path.iterdir()
                },
                before,
            )

            marker_bytes = (plain_marker.read_bytes(), archive_marker.read_bytes())
            self.assertTrue(prepare.mark_legacy_parts(root))
            self.assertEqual(
                (plain_marker.read_bytes(), archive_marker.read_bytes()), marker_bytes
            )

    def test_default_prepare_restores_only_marked_parts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            approved = root / "approved"
            unapproved = root / "unapproved"
            approved.mkdir()
            unapproved.mkdir()
            make_parts(approved, "notes.bin", b"approved plain")
            make_parts(approved, "images.zip", zip_content("images"))
            unmarked_plain = make_parts(unapproved, "keep.bin", b"unapproved plain")
            unmarked_archive = make_parts(
                unapproved, "keep-images.zip", zip_content("keep-images")
            )
            self.assertTrue(prepare.mark_legacy_parts(approved))

            prepare.prepare_split_files(root)
            prepare.restore_tidy_archives(root)

            self.assertEqual((approved / "notes.bin").read_bytes(), b"approved plain")
            self.assertFalse((approved / "notes.bin.parts").exists())
            self.assertFalse((approved / "notes.bin.parts.prepare.json").exists())
            self.assertEqual((approved / "images" / "item.txt").read_text(), "restored")
            self.assertFalse((approved / "images.zip.parts").exists())
            self.assertFalse((approved / "images.zip.archive.json").exists())
            self.assertTrue(unmarked_plain.exists())
            self.assertTrue(unmarked_archive.exists())
            self.assertFalse((unapproved / "keep.bin").exists())
            self.assertFalse((unapproved / "keep-images").exists())

    def test_marking_rejects_unsafe_manifests_conflicting_markers_and_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            unsafe_parts = root / "unsafe.parts"
            unsafe_parts.mkdir()
            (unsafe_parts / "manifest.json").write_text(
                json.dumps(
                    {
                        "original_name": "../outside",
                        "original_size": 1,
                        "part_count": 1,
                    }
                ),
                encoding="utf-8",
            )
            (unsafe_parts / "unsafe.part001").write_bytes(b"x")

            conflict_parts = make_parts(root, "conflict.bin", b"conflict")
            conflict_marker = root / "conflict.bin.parts.prepare.json"
            conflict_marker.write_text("{}", encoding="utf-8")

            target_parts = make_parts(root, "target.bin", b"target")
            (root / "target.bin").write_bytes(b"existing target")

            extra_parts = make_parts(root, "extra.bin", b"extra")
            (extra_parts / "unexpected.txt").write_text("unexpected", encoding="utf-8")

            self.assertFalse(prepare.mark_legacy_parts(root))
            self.assertTrue(unsafe_parts.exists())
            self.assertFalse((root / "unsafe.parts.prepare.json").exists())
            self.assertEqual(conflict_marker.read_text(encoding="utf-8"), "{}")
            self.assertTrue(conflict_parts.exists())
            self.assertTrue(target_parts.exists())
            self.assertFalse((root / "target.bin.parts.prepare.json").exists())
            self.assertTrue(extra_parts.exists())
            self.assertFalse((root / "extra.bin.parts.prepare.json").exists())

    def test_default_prepare_skips_invalid_marker_without_merging(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            parts_path = make_parts(root, "unsafe.bin", b"do not merge")
            marker_path = root / "unsafe.bin.parts.prepare.json"
            marker_path.write_text(
                json.dumps(
                    {
                        "format_version": 1,
                        "parts_directory_name": "other.parts",
                        "original_name": "unsafe.bin",
                    }
                ),
                encoding="utf-8",
            )

            prepare.prepare_split_files(root)

            self.assertTrue(parts_path.exists())
            self.assertTrue(marker_path.exists())
            self.assertFalse((root / "unsafe.bin").exists())

    def test_default_prepare_skips_marked_parts_with_an_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            parts_path = make_parts(root, "existing.bin", b"parts content")
            marker_path = root / "existing.bin.parts.prepare.json"
            prepare.write_legacy_parts_marker(marker_path, parts_path, "existing.bin")
            (root / "existing.bin").write_bytes(b"existing target")

            prepare.prepare_split_files(root)

            self.assertTrue(parts_path.exists())
            self.assertTrue(marker_path.exists())
            self.assertEqual((root / "existing.bin").read_bytes(), b"existing target")


if __name__ == "__main__":
    unittest.main()
