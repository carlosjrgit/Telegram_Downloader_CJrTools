import hashlib
import tempfile
import unittest
from pathlib import Path

from modules.integrity import compute_sha256, verify_file_integrity


class TestIntegrity(unittest.TestCase):

    def test_compute_sha256_and_verify(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "sample.txt"
            content = b"Conteudo de teste para integridade SHA-256."
            test_file.write_bytes(content)

            expected_sha = hashlib.sha256(content).hexdigest()
            calculated_sha = compute_sha256(test_file)

            self.assertEqual(calculated_sha, expected_sha)
            self.assertTrue(verify_file_integrity(test_file, len(content), expected_sha))

    def test_verify_file_integrity_failures(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "sample.txt"
            test_file.write_bytes(b"12345")

            # Wrong size
            self.assertFalse(verify_file_integrity(test_file, 10))

            # Wrong hash
            self.assertFalse(verify_file_integrity(test_file, 5, "wrong_hash"))

            # Non-existent file
            self.assertFalse(verify_file_integrity(Path(tmp_dir) / "nao_existe.txt", 5))


if __name__ == "__main__":
    unittest.main()
