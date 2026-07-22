from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

INSTALLER = Path(__file__).parents[1] / "install.py"
SPEC = importlib.util.spec_from_file_location("installer", INSTALLER)
installer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def test_project_destinations_match_agent_discovery_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            found = dict(installer.destinations(["claude", "codex"], "project", root))
            self.assertEqual(found["claude"], root / ".claude" / "skills" / installer.SKILL_NAME)
            self.assertEqual(found["codex"], root / ".agents" / "skills" / installer.SKILL_NAME)

    def test_existing_install_requires_force(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / installer.SKILL_NAME
            destination.mkdir()
            with self.assertRaises(FileExistsError):
                installer.install(destination, force=False, dry_run=False)


if __name__ == "__main__":
    unittest.main()
