import csv
import tempfile
import unittest
from pathlib import Path

from modules.export import export_catalog_csv, sanitize_csv_cell


class TestCSVSecurity(unittest.TestCase):

    def test_sanitize_csv_cell_neutralizes_formulas(self):
        self.assertEqual(sanitize_csv_cell("=1+1"), "'=1+1")
        self.assertEqual(sanitize_csv_cell("+cmd|' /C calc'!A0"), "'+cmd|' /C calc'!A0")
        self.assertEqual(sanitize_csv_cell("-SUM(A1:A10)"), "'-SUM(A1:A10)")
        self.assertEqual(sanitize_csv_cell("@SUM(1,2)"), "'@SUM(1,2)")
        self.assertEqual(sanitize_csv_cell("\tformula"), "'\tformula")
        self.assertEqual(sanitize_csv_cell("Texto Normal.pdf"), "Texto Normal.pdf")
        self.assertEqual(sanitize_csv_cell(12345), 12345)

    def test_export_catalog_csv(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_file = Path(tmp_dir) / "test_catalog.csv"
            sample_data = [
                {
                    "message_id": 101,
                    "file_name": "=SUM(1+1).pdf",
                    "extension": ".pdf",
                    "mime_type": "application/pdf",
                    "file_size": 2048,
                    "date": "2026-01-01 12:00:00"
                },
                {
                    "message_id": 102,
                    "file_name": "Aula 01.mp4",
                    "extension": ".mp4",
                    "mime_type": "video/mp4",
                    "file_size": 10485760,
                    "date": "2026-01-01 12:05:00"
                }
            ]

            result_path = export_catalog_csv(sample_data, csv_file)
            self.assertTrue(Path(result_path).exists())

            with open(csv_file, encoding="utf-8-sig") as f:
                reader = list(csv.reader(f, delimiter=";"))
                self.assertEqual(len(reader), 3)  # Header + 2 rows
                self.assertEqual(reader[1][2], "'=SUM(1+1).pdf")  # Neutralized
                self.assertEqual(reader[2][2], "Aula 01.mp4")


if __name__ == "__main__":
    unittest.main()
