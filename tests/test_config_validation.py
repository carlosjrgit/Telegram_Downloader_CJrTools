import json
import os
import tempfile
import unittest
from pathlib import Path

from config import Config, ConfigError


class TestConfigValidation(unittest.TestCase):

    def test_config_defaults(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg_file = Path(tmp_dir) / "config.json"
            cfg = Config(cfg_file)
            self.assertEqual(cfg.concurrent_downloads, 3)
            self.assertEqual(cfg.retry_attempts, 5)
            self.assertEqual(cfg.chunk_size, 524288)
            self.assertTrue(cfg.verify_integrity)

    def test_config_valid_load_and_save(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg_file = Path(tmp_dir) / "config.json"
            data = {
                "api_id": 123456,
                "api_hash": "abcdef1234567890",
                "phone": "+5511999999999",
                "download_path": "./downloads",
                "chunk_size": 262144,
                "concurrent_downloads": 4,
                "retry_attempts": 3,
                "verify_integrity": "false",  # test string bool parsing
                "save_hash": True,
                "overwrite_existing": False,
                "auto_resume": True,
                "log_level": "DEBUG"
            }
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump(data, f)

            cfg = Config(cfg_file)
            cfg.load()
            self.assertEqual(cfg.api_id, 123456)
            self.assertFalse(cfg.verify_integrity)
            self.assertEqual(cfg.log_level, "DEBUG")

    def test_config_invalid_ranges(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg_file = Path(tmp_dir) / "config.json"

            # Negative concurrent_downloads
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump({"concurrent_downloads": -5}, f)
            cfg = Config(cfg_file)
            with self.assertRaises(ConfigError):
                cfg.load()

            # Out of bounds chunk_size (too small)
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump({"chunk_size": 100}, f)
            cfg = Config(cfg_file)
            with self.assertRaises(ConfigError):
                cfg.load()

            # Invalid log level
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump({"log_level": "SUPER_VERBOSE"}, f)
            cfg = Config(cfg_file)
            with self.assertRaises(ConfigError):
                cfg.load()

    def test_config_env_vars_override(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg_file = Path(tmp_dir) / "config.json"
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump({"api_id": 11111, "api_hash": "json_hash", "phone": "+11111"}, f)

            old_env = dict(os.environ)
            try:
                os.environ["TELEGRAM_API_ID"] = "99999"
                os.environ["TELEGRAM_API_HASH"] = "env_hash"
                os.environ["TELEGRAM_PHONE"] = "+99999"

                cfg = Config(cfg_file)
                cfg.load()

                self.assertEqual(cfg.api_id, 99999)
                self.assertEqual(cfg.api_hash, "env_hash")
                self.assertEqual(cfg.phone, "+99999")
            finally:
                os.environ.clear()
                os.environ.update(old_env)


if __name__ == "__main__":
    unittest.main()
