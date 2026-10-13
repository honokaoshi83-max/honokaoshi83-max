import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from PySide6.QtWidgets import QApplication, QPlainTextEdit
from PySide6.QtCore import QProcess
from PySide6.QtTest import QTest
from simulator_guide import SimulatorGuide

class ProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        state = dict(root=root, ini=root/'config.ini', installed=True, configured=True, integrated=True)
        self.mock = patch('simulator_guide.inspect_simulator', return_value=state); self.mock.start()
        self.guide = SimulatorGuide(SimpleNamespace(project=root, root=root, python=sys.executable))
    def tearDown(self):
        self.guide.progress_timer.stop(); self.guide.close(); self.mock.stop(); self.temp.cleanup()
    def test_simulation_waits_for_real_success(self):
        self.guide.begin_progress()
        self.assertEqual(self.guide.progress.value(), 1)
        self.assertFalse(self.guide.findChildren(QPlainTextEdit))
        for _ in range(150): self.guide.advance_progress()
        self.assertEqual(self.guide.progress.value(), 99)
        self.guide.on_task_finished(0, QProcess.NormalExit)
        self.assertEqual(self.guide.progress.value(), 100)
        self.assertIn('重新检测', self.guide.progress_note.text())
        self.assertIn('重启', self.guide.progress_note.text())
        self.assertFalse(self.guide.progress_timer.isActive())
    def test_crash_is_not_success_even_with_zero_code(self):
        self.guide.begin_progress(); self.guide.on_task_finished(0, QProcess.CrashExit)
        self.assertLess(self.guide.progress.value(), 100)
        self.assertIn('未完成', self.guide.progress_note.text())
        self.assertFalse(self.guide.progress_timer.isActive())
    def test_diagnostics_are_saved_without_visible_log(self):
        self.guide.message('测试诊断')
        self.assertIn('测试诊断', self.guide.log_path.read_text(encoding='utf-8'))
    def test_real_process_success_and_nonzero_failure(self):
        self.guide.run(sys.executable, ['-c', 'print("done")'])
        for _ in range(250):
            QTest.qWait(20)
            if not self.guide.task_active: break
        self.assertFalse(self.guide.task_active)
        self.assertEqual(self.guide.progress.value(), 100)
        self.guide.run(sys.executable, ['-c', 'raise SystemExit(1)'])
        for _ in range(250):
            QTest.qWait(20)
            if not self.guide.task_active: break
        self.assertFalse(self.guide.task_active)
        self.assertLess(self.guide.progress.value(), 100)
        self.assertIn('未完成', self.guide.progress_note.text())

if __name__ == '__main__': unittest.main()
