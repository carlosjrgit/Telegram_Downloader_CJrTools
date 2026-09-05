import os
import tempfile
import unittest
from pathlib import Path

from modules.downloader import check_available_disk_space


class TestDownloaderFlow(unittest.TestCase):

    def test_check_available_disk_space(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Check for a small reasonable size (1 MB)
            self.assertTrue(check_available_disk_space(Path(tmp_dir), 1024 * 1024))
            # Check for an impossibly huge size (100 Petabytes)
            impossibly_huge = 100 * 1024 * 1024 * 1024 * 1024 * 1024
            self.assertFalse(check_available_disk_space(Path(tmp_dir), impossibly_huge))

    def test_atomic_part_simulation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            target_file = Path(tmp_dir) / "video_aula.mp4"
            part_file = Path(str(target_file) + ".part")

            # Simulate streaming into .part
            part_file.write_bytes(b"Simulated video chunk 1 and 2")
            self.assertTrue(part_file.exists())
            self.assertFalse(target_file.exists())

            # Atomic replace
            os.replace(part_file, target_file)

            self.assertFalse(part_file.exists())
            self.assertTrue(target_file.exists())
            self.assertEqual(target_file.read_bytes(), b"Simulated video chunk 1 and 2")


if __name__ == "__main__":
    unittest.main()
