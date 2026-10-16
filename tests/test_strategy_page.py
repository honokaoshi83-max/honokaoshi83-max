import os,sys,tempfile,unittest
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from PySide6.QtWidgets import QApplication
from strategy_page import StrategyPage
from race_strategy import load_plan

class StrategyPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.page=StrategyPage(Path(self.temp.name));self.addCleanup(self.page.deleteLater)
    def fill(self):
        self.page.enabled.setChecked(True)
        self.page.name.setText('耐力赛');self.page.track.setCurrentText('纽博格林耐力布局');self.page.car.setCurrentText('思域 TCR')
        for key,value in dict(initial_fuel=50,capacity=60,lap_minutes=8,lap_seconds=0,burn=4).items():self.page.fields[key].setValue(value)
    def test_missing_data_does_not_generate_result(self):
        self.page.generate();self.assertIsNone(self.page.result);self.assertEqual(self.page.table.rowCount(),0)
    def test_generate_and_edit_invalidates_previous_result(self):
        self.fill();self.page.generate();self.assertEqual(self.page.result['stops'],2)
        self.assertEqual(self.page.table.rowCount(),2)
        self.page.fields['burn'].setValue(5)
        self.assertIsNone(self.page.result);self.assertEqual(self.page.table.rowCount(),0)
    def test_save_and_reopen_keeps_user_conditions(self):
        self.fill();self.page.save()
        self.assertEqual(load_plan(self.page.path)['initial_fuel'],50)
        other=StrategyPage(Path(self.temp.name));self.addCleanup(other.deleteLater)
        self.assertEqual(other.car.currentText(),'思域 TCR');self.assertEqual(other.fields['burn'].value(),4)
    def test_failed_save_is_reported(self):
        self.fill()
        with patch('strategy_page.save_plan',side_effect=OSError('read only')):self.page.save()
        self.assertIn('保存失败',self.page.notice.text())
    def test_real_connection_is_not_claimed_as_live_strategy_execution(self):
        self.page.enabled.setChecked(True)
        self.page.update_connection(dict(game=True,track='筑波',car='BMW',fuel=23))
        self.assertIn('筑波',self.page.connection.text());self.assertIn('尚未启用',self.page.connection.text())
    def test_disabled_by_default_and_never_computes_or_updates_telemetry(self):
        self.assertFalse(self.page.enabled.isChecked())
        with patch('strategy_page.calculate_plan') as compute:
            self.page.generate();compute.assert_not_called()
        self.page.update_connection(dict(game=True,track='不应显示',fuel=20))
        self.assertNotIn('不应显示',self.page.connection.text());self.assertIn('已关闭',self.page.connection.text())
    def test_switch_off_clears_result_and_persists(self):
        self.fill();self.page.save();self.page.generate();self.assertIsNotNone(self.page.result)
        self.page.enabled.setChecked(False);self.assertIsNone(self.page.result)
        other=StrategyPage(Path(self.temp.name));self.addCleanup(other.deleteLater)
        self.assertFalse(other.enabled.isChecked());self.assertEqual(other.fields['burn'].value(),4)

if __name__=='__main__':unittest.main()
