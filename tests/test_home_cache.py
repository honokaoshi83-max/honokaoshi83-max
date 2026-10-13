import os,sys,tempfile,unittest
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QVBoxLayout
from main import Window

class HomeOnly(Window):
    def __init__(self,root):
        QMainWindow.__init__(self)
        self.backend=SimpleNamespace(root=root);self.state={};self.job=None
        self.host=QWidget();self.setCentralWidget(self.host);self.layout=QVBoxLayout(self.host)
        self.build_home();self.run_python=Mock(return_value=True)
    def page(self,*args):return self.layout

class CacheHomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_home_action_and_conditions(self):
        with tempfile.TemporaryDirectory() as d:
            window=HomeOnly(Path(d))
            self.assertTrue(window.host.isAncestorOf(window.cache_button))
            self.assertEqual(window.cache_button.objectName(),'primary')
            window.cache_button.click();window.run_python.assert_not_called()
            self.assertIn('启动播报',window.cache_status.text())
            window.state={'health':{'status':'ready'},'game':True}
            window.cache_button.click();window.run_python.assert_not_called()
            self.assertIn('驾驶会话',window.cache_status.text())
            window.state={'health':{'status':'ready'},'game':False}
            window.cache_button.click()
            window.run_python.assert_called_once_with('warm_cache.py',kind='cache')
            self.assertFalse(window.cache_button.isEnabled())
            window.deleteLater()

if __name__=='__main__':unittest.main()
