"""Exercise the installer with fake tools: tests never install system packages."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


INSTALLER = Path(__file__).resolve().parents[1] / "install.sh"


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.bin = self.folder / "bin"
        self.bin.mkdir()
        self.state = self.folder / "state"
        self.state.mkdir()
        self.log = self.folder / "brew.log"
        self.env = {**os.environ, "PATH": f"{self.bin}:/usr/bin:/bin",
                    "SIM_STATE": str(self.state), "SIM_LOG": str(self.log),
                    "SIM_PREFIX": str(self.folder)}
        self.tool("uname", "echo Darwin")
        self.tool("python3", '[ -f "$SIM_STATE/python" ]')
        self.tool("pdftotext", '[ -f "$SIM_STATE/poppler" ]')
        self.tool("pdftoppm", '[ -f "$SIM_STATE/poppler" ]')
        self.tool("chafa", '[ -f "$SIM_STATE/chafa" ]')
        self.tool("brew", '''if [ "$1" = --prefix ]; then
    echo "$SIM_PREFIX"
elif [ "$1" = install ]; then
    shift
    for package in "$@"; do
        echo "$package" >> "$SIM_LOG"
        touch "$SIM_STATE/$package"
    done
else
    exit 2
fi''')

    def tool(self, name, body, directory=None):
        target = (directory or self.bin) / name
        target.write_text("#!/bin/bash\n" + body + "\n")
        target.chmod(0o755)

    def run_installer(self, *arguments):
        return subprocess.run(["/bin/bash", str(INSTALLER), *arguments], env=self.env,
                              text=True, capture_output=True, timeout=10)

    def ready(self, *names):
        for name in names:
            (self.state / name).touch()

    def test_check_reports_missing_without_running_brew(self):
        result = self.run_installer("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MANQUANT", result.stdout)
        self.assertFalse(self.log.exists())

    def test_ready_machine_needs_no_installation(self):
        self.ready("python", "poppler", "chafa")
        for arguments in ((), ("--check",)):
            result = self.run_installer(*arguments)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.log.exists())

    def test_installs_only_missing_package_and_can_be_rerun(self):
        self.ready("python", "poppler")
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.log.read_text().splitlines(), ["chafa"])
        second = self.run_installer()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(self.log.read_text().splitlines(), ["chafa"])

    def test_all_missing_packages_are_installed(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.log.read_text().splitlines(), ["python", "poppler", "chafa"])

    def test_existing_brew_prefix_is_checked_before_installation(self):
        self.ready("python", "poppler", "chafa")
        prefix = self.folder / "homebrew"
        tools = prefix / "bin"
        tools.mkdir(parents=True)
        for name in ("python3", "pdftotext", "pdftoppm", "chafa"):
            (self.bin / name).rename(tools / name)
        self.env["SIM_PREFIX"] = str(prefix)
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.log.exists())
        self.assertIn("export PATH=", result.stdout)

    def test_failed_installation_stops_with_failure(self):
        self.tool("brew", 'if [ "$1" = --prefix ]; then echo "$SIM_PREFIX"; else exit 17; fi')
        self.assertEqual(self.run_installer().returncode, 17)

    def test_unsupported_platform_or_option_does_not_install(self):
        self.assertEqual(self.run_installer("--unknown").returncode, 2)
        self.tool("uname", "echo Linux")
        self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
