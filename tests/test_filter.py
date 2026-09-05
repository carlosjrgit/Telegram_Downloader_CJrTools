import unittest

from modules.filter import FileFilter, normalize_text


class TestFileFilter(unittest.TestCase):

    def test_normalize_text(self):
        self.assertEqual(normalize_text("Mônica"), "monica")
        self.assertEqual(normalize_text("Introdução à Computação"), "introducao a computacao")
        self.assertEqual(normalize_text("AULA_01.MP4"), "aula_01.mp4")

    def test_filter_all(self):
        filt = FileFilter(mode="ALL")
        self.assertTrue(filt.should_download("video.mp4", "video/mp4"))
        self.assertTrue(filt.should_download("documento.pdf", "application/pdf"))

    def test_filter_include_and_exclude(self):
        filt = FileFilter(
            mode="CUSTOM",
            include_terms=["Aula", ".mp4"],
            exclude_terms=["Gabarito", "Exercicio"]
        )

        # Matched include, not in exclude
        self.assertTrue(filt.should_download("Aula 01 Introdução.mp4", "video/mp4"))
        self.assertTrue(filt.should_download("aula 02.mkv", "video/x-matroska"))

        # In exclude list
        self.assertFalse(filt.should_download("Aula 01 - Gabarito.mp4", "video/mp4"))
        self.assertFalse(filt.should_download("Exercicio de Aula.mp4", "video/mp4"))

        # Not in include list
        self.assertFalse(filt.should_download("Apresentacao.pdf", "application/pdf"))


if __name__ == "__main__":
    unittest.main()
