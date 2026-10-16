import os,sys,tempfile,unittest
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'work/race-voices'))
from PySide6.QtWidgets import QApplication
from main import Window

class NavigationOnly(Window):
    def build_home(self):self.page('运行概览','')
    def build_voices(self):self.page('音色管理','')
    def tick(self):pass

class NavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_four_pages_keep_matching_nav_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            win=NavigationOnly(SimpleNamespace(project=Path(tmp),root=Path(tmp)))
            try:
                self.assertEqual(win.pages.count(),5)
                self.assertIn('测试中',win.nav.item(1).text())
                win.nav.setCurrentRow(1);self.assertIs(win.pages.currentWidget(),win.strategy_page)
                self.assertFalse(win.strategy_page.enabled.isChecked())
                win.nav.setCurrentRow(2);self.assertIn('音色管理',win.pages.currentWidget().widget().layout().itemAt(0).widget().text())
                win.nav.setCurrentRow(3);self.assertIs(win.pages.currentWidget(),win.reviews_page)
                win.nav.setCurrentRow(4);self.assertTrue(win.pages.currentWidget().isAncestorOf(win.diag))
            finally:
                win.closing=True;win.timer.stop();win.reviews_page.timer.stop();win.pool.shutdown(wait=False);win.tray.hide();win.close();win.deleteLater()

if __name__=='__main__':unittest.main()
