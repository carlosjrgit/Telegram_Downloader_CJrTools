import tempfile
import unittest
from pathlib import Path

from modules.database import Database


class TestDatabase(unittest.TestCase):

    def test_database_initialization_and_operations(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_file = Path(tmp_dir) / "test_downloads.db"
            db = Database(db_file)
            db.initialize()

            # 1. Upsert file
            file_data = {
                "message_id": 1,
                "file_id": "file_123",
                "file_name": "aula_1.mp4",
                "file_size": 1048576,
                "mime_type": "video/mp4",
                "extension": ".mp4",
                "local_path": str(Path(tmp_dir) / "aula_1.mp4"),
                "status": "PENDING"
            }
            db.upsert_file(file_data)

            # 2. Get file
            record = db.get_file(1, "file_123")
            self.assertIsNotNone(record)
            self.assertEqual(record["file_name"], "aula_1.mp4")
            self.assertEqual(record["status"], "PENDING")

            # 3. Update progress & status
            db.update_progress(1, "file_123", 524288)
            db.update_status(1, "file_123", "COMPLETED", hash_value="fake_hash_123")

            updated = db.get_file(1, "file_123")
            self.assertEqual(updated["status"], "COMPLETED")
            self.assertEqual(updated["hash"], "fake_hash_123")
            self.assertEqual(updated["downloaded_bytes"], 524288)

            # 4. Session info
            db.save_session_info(entity_id=98765, entity_title="Curso Python", dest_path=str(tmp_dir))
            sess = db.get_session_info()
            self.assertIsNotNone(sess)
            self.assertEqual(sess["entity_title"], "Curso Python")
            self.assertEqual(sess["entity_id"], "98765")

            # 5. Summary counts
            summary = db.get_summary_counts()
            self.assertEqual(summary["total_files"], 1)
            self.assertEqual(summary["completed_files"], 1)

            db.close()


if __name__ == "__main__":
    unittest.main()
