import tempfile
import unittest
from pathlib import Path

from modules.paths import get_app_data_dir, get_config_path, get_database_path, get_session_dir
from modules.utils import safe_join


class TestPaths(unittest.TestCase):

    def test_safe_join_valid(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir) / "downloads"
            base.mkdir()
            result = safe_join(base, "video_1.mp4")
            self.assertEqual(result, (base / "video_1.mp4").resolve())

    def test_safe_join_subfolder(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir) / "downloads"
            base.mkdir()
            result = safe_join(base, "curso/aula_1.mp4")
            self.assertEqual(result, (base / "curso" / "aula_1.mp4").resolve())

    def test_safe_join_rejects_escape(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir) / "downloads"
            base.mkdir()

            with self.assertRaises(ValueError):
                safe_join(base, "../../../secret.txt")

            with self.assertRaises(ValueError):
                safe_join(base, "..\\..\\windows\\system32")

    def test_paths_functions_exist_and_return_path(self):
        app_dir = get_app_data_dir()
        self.assertIsInstance(app_dir, Path)

        cfg = get_config_path()
        self.assertIsInstance(cfg, Path)

        db = get_database_path()
        self.assertIsInstance(db, Path)

        sess = get_session_dir()
        self.assertIsInstance(sess, Path)


if __name__ == "__main__":
    unittest.main()
