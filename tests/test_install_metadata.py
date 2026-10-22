import unittest
from pathlib import Path


class PortableInstallTests(unittest.TestCase):
    def test_dependencies_do_not_embed_relative_file_urls(self):
        text = (Path(__file__).resolve().parents[1] / 'pyproject.toml').read_text()
        self.assertNotIn(' @ file:', text)

    def test_local_audio_dependency_excludes_incompatible_pyav(self):
        text = (Path(__file__).resolve().parents[1] / 'pyproject.toml').read_text()
        self.assertIn('av>=15,<17', text)
