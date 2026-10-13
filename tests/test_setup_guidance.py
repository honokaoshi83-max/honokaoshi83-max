from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SetupGuidanceTests(unittest.TestCase):
    def test_finish_action_installs_simulator_controller_by_default_and_explains_missing_features(self):
        setup = (ROOT / "scripts" / "desktop-setup.iss").read_text(encoding="utf-8-sig")
        run_section = setup.split("[Run]", 1)[1].split("[UninstallRun]", 1)[0]
        launcher = (ROOT / "scripts" / "install-simulator-controller.ps1").read_text(encoding="utf-8-sig")

        self.assertIn('--install-simulator', run_section)
        self.assertIn('{app}\\iracing-assistant.exe', run_section)
        self.assertIn("postinstall", run_section.lower())
        self.assertNotIn("unchecked", run_section.lower())
        self.assertIn("取消后无邻车、旗号、策略播报", run_section)
        self.assertIn("simulatorcontroller.s3.eu-central-1.amazonaws.com", launcher)
        self.assertIn("Invoke-WebRequest", launcher)
        self.assertIn("Start-Process", launcher)


if __name__ == "__main__":
    unittest.main()
