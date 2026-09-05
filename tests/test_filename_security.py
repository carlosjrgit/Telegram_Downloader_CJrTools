import unittest

from modules.utils import sanitize_filename, sanitize_log_text


class TestFilenameSecurity(unittest.TestCase):

    def test_sanitize_filename_removes_path_traversal(self):
        self.assertEqual(sanitize_filename("../../etc/passwd"), "passwd")
        self.assertEqual(sanitize_filename("..\\..\\windows\\system32\\calc.exe"), "calc.exe")
        self.assertEqual(sanitize_filename("/var/log/syslog"), "syslog")
        self.assertEqual(sanitize_filename("C:\\Windows\\explorer.exe"), "explorer.exe")

    def test_sanitize_filename_windows_reserved_names(self):
        self.assertEqual(sanitize_filename("CON"), "safe_CON")
        self.assertEqual(sanitize_filename("con.txt"), "safe_con.txt")
        self.assertEqual(sanitize_filename("PRN.pdf"), "safe_PRN.pdf")
        self.assertEqual(sanitize_filename("AUX"), "safe_AUX")
        self.assertEqual(sanitize_filename("NUL.zip"), "safe_NUL.zip")
        self.assertEqual(sanitize_filename("COM1.mp4"), "safe_COM1.mp4")
        self.assertEqual(sanitize_filename("lpt1.mkv"), "safe_lpt1.mkv")

    def test_sanitize_filename_invalid_characters(self):
        self.assertEqual(sanitize_filename('video:aula*1?"<>|.mp4'), "video_aula_1_____.mp4")
        self.assertEqual(sanitize_filename("arquivo\x00nulo.txt"), "arquivo_nulo.txt")
        self.assertEqual(sanitize_filename("arquivo\ncom\nnewline.pdf"), "arquivo_com_newline.pdf")
        self.assertEqual(sanitize_filename("arquivo\rcom\rcarriage.pdf"), "arquivo_com_carriage.pdf")

    def test_sanitize_filename_empty_and_spaces(self):
        self.assertEqual(sanitize_filename(""), "unnamed_file")
        self.assertEqual(sanitize_filename("   ...  "), "unnamed_file")
        self.assertEqual(sanitize_filename("meu_arquivo.pdf. . "), "meu_arquivo.pdf")

    def test_sanitize_filename_length_limitation(self):
        long_stem = "A" * 300
        filename = f"{long_stem}.mp4"
        sanitized = sanitize_filename(filename, max_length=180)
        self.assertLessEqual(len(sanitized), 180)
        self.assertTrue(sanitized.endswith(".mp4"))

    def test_sanitize_log_text(self):
        raw_log = "User input\r\nFAKE_LOG_ENTRY: Admin logged in\n"
        cleaned = sanitize_log_text(raw_log)
        self.assertNotIn("\r", cleaned)
        self.assertNotIn("\n", cleaned)
        self.assertIn("User input  FAKE_LOG_ENTRY: Admin logged in ", cleaned)


if __name__ == "__main__":
    unittest.main()
