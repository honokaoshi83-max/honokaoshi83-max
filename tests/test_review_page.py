import os,sys,tempfile,unittest
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from unittest.mock import patch
SOURCE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SOURCE/'app'));sys.path.insert(0,str(SOURCE/'work/race-voices'))
from PySide6.QtWidgets import QApplication
from reviews_page import ReviewsPage,lap_stats
from review_store import save_review

class ReviewPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_empty_and_latest_only_and_file_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);page=ReviewsPage(root)
            try:
                self.assertEqual(page.entries,[])
                for i in range(7):save_review(root,dict(id=str(i),saved_at=f'2026-10-15T12:00:0{i}+09:00',mode='time_trial',track='筑波',summary=['评价']))
                page.refresh(force=True);self.assertEqual(len(page.entries),1)
                self.assertEqual(page.entries[0]['id'],'6')
                with patch('reviews_page.subprocess.Popen') as launch:page.reveal(page.entries[0]['path'])
                self.assertEqual(launch.call_args.args[0],['explorer.exe','/select,',page.entries[0]['path']])
                with patch('reviews_page.subprocess.Popen') as launch:page.reveal(str(root.parent/'outside.txt'))
                launch.assert_not_called()
                self.assertFalse(page.notice.isHidden())
            finally:page.timer.stop();page.deleteLater()

    def test_latest_only_dashboard_empty_and_race_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);page=ReviewsPage(root)
            try:
                self.assertEqual(page.latest_title.text(),'最近一次比赛')
                self.assertFalse(page.open_latest.isEnabled())
                self.assertIn('—',page.details.item(0,1).text())
                for i in range(7):
                    save_review(root,dict(id=str(i),saved_at=f'2026-10-15T12:00:0{i}+09:00',ended_at=f'2026-10-15T12:00:0{i}+09:00',
                        started_at='2026-10-15T11:30:00+09:00',mode='race',track=f'赛道{i}',car='BMW M2',layout='全程',
                        position=4,class_position=2,cars=24,grid=7,completed=10,total_seconds=1800,observed_seconds=1800,summary=['发挥稳定。']))
                page.refresh(force=True)
                self.assertEqual(len(page.entries),1)
                self.assertIn('赛道6',page.latest_title.text())
                values=' '.join(page.details.item(r,c).text() for r in range(page.details.rowCount()) for c in range(page.details.columnCount()))
                self.assertIn('总排名',values);self.assertIn('4 / 24',values);self.assertIn('+3',values)
                self.assertIn('30分00秒',values);self.assertEqual(page.evaluation.text(),'发挥稳定。')
                self.assertEqual(len(list((root/'复盘').glob('*.txt'))),7)
                with patch('reviews_page.subprocess.Popen') as launch:page.open_latest.click()
                self.assertEqual(launch.call_args.args[0][-1],page.entries[0]['path'])
            finally:page.timer.stop();page.deleteLater()

    def test_time_trial_metrics_exclude_ranking_and_missing_data_are_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            stats=dict(observed_laps=3,timed_laps=3,valid_laps=2,invalid_laps=1,best_valid=60.123,valid_average=61.5,standard_deviation=1.2,stability='poor')
            save_review(root,dict(id='tt',saved_at='2026-10-15T12:00:00+09:00',mode='time_trial',track='筑波2000',stats=stats,summary=['需要减少犯规。']))
            page=ReviewsPage(root)
            try:
                values=' '.join(page.details.item(r,c).text() for r in range(page.details.rowCount()) for c in range(page.details.columnCount()))
                self.assertNotIn('排名',values);self.assertIn('1分00.123秒',values);self.assertIn('33.3%',values)
                self.assertIn('—',values);self.assertIn('需要减少犯规',page.evaluation.text())
            finally:page.timer.stop();page.deleteLater()

    def test_race_display_metrics_keep_invalid_laps_out_of_valid_average(self):
        row=dict(laps=[dict(seconds=100,valid=True),dict(seconds=102,valid=True),dict(seconds=130,valid=False),dict(seconds=None,valid=False)])
        result=lap_stats(row)
        self.assertEqual(result['observed_laps'],4);self.assertEqual(result['invalid_laps'],2)
        self.assertEqual(result['best_valid'],100);self.assertEqual(result['valid_average'],101)
        self.assertGreater(result['standard_deviation'],10)

    def test_dashboard_fits_current_page_without_outer_scrolling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            summary=['本场正式总排名第六名，组别第二名，比发车位置提升三位。',
                '本次正赛记录八个完成圈，其中七个有效计时圈，一个犯规无效圈。',
                '最快有效圈一分四十秒三，有效平均圈速一分四十一秒二。',
                '后半段有效圈平均比前半段快零点四秒。',
                '有效计时圈之间的节奏稳定。犯规无效圈仍影响了本次的整体稳定性。',
                '记录中最长连续完成四个有效圈。',
                '犯规无效圈占已记录完成圈的百分之十二点五。',
                '下一场先减少犯规，把连续有效圈跑稳，再逐步提高速度。']
            save_review(root,dict(id='fit',mode='race',track='纽博格林综合耐力布局',saved_at='2026-10-15T12:00:00+09:00',summary=summary,position=6,grid=9))
            page=ReviewsPage(root)
            try:
                from main import STYLE
                page.setStyleSheet(STYLE)
                for height in (760,650):
                    page.resize(1040,height);page.show()
                    for _ in range(5):self.app.processEvents()
                    self.assertEqual(page.verticalScrollBar().maximum(),0)
                    self.assertLessEqual(page.evaluation_panel.geometry().bottom(),page.viewport().height())
                    ratio=page.data_panel.height()/page.evaluation_panel.height()
                    self.assertGreaterEqual(ratio,1.45);self.assertLessEqual(ratio,5.15)
                    for paragraph in summary:self.assertIn(paragraph,page.evaluation.text())
                    self.assertLessEqual(sum(page.details.rowHeight(r) for r in range(page.details.rowCount())),page.details.viewport().height()+2)
            finally:page.timer.stop();page.close();page.deleteLater()

    def test_comment_area_grows_with_text_and_stops_at_three_to_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);page=ReviewsPage(root)
            try:
                from main import STYLE
                page.setStyleSheet(STYLE);page.resize(1040,760);page.show()
                def settle():
                    for _ in range(8):self.app.processEvents()
                settle()
                self.assertAlmostEqual(page.data_panel.height()/page.evaluation_panel.height(),5,delta=.15)
                save_review(root,dict(id='dynamic',mode='race',track='筑波2000',saved_at='2026-10-15T12:00:00+09:00',summary=['发挥稳定。']))
                page.refresh(force=True);settle();short=page.evaluation_panel.height()
                self.assertAlmostEqual(page.data_panel.height()/short,5,delta=.15)
                page.evaluation.setText('\n'.join(['本场比赛节奏稳定，后半段平均圈速有所提高。']*5));settle()
                medium=page.evaluation_panel.height()
                self.assertGreater(medium,short)
                self.assertGreater(page.data_panel.height()/medium,1.55)
                self.assertEqual(page.evaluation.verticalScrollBar().maximum(),0)
                page.evaluation.setText('\n'.join(['本场比赛节奏稳定，后半段平均圈速有所提高。']*50));settle()
                self.assertAlmostEqual(page.data_panel.height()/page.evaluation_panel.height(),1.5,delta=.08)
                self.assertEqual(page.verticalScrollBar().maximum(),0)
                self.assertGreater(page.evaluation.verticalScrollBar().maximum(),0)
                page.evaluation.setText('发挥稳定。');settle()
                self.assertAlmostEqual(page.data_panel.height()/page.evaluation_panel.height(),5,delta=.15)
            finally:page.timer.stop();page.close();page.deleteLater()

if __name__=='__main__':unittest.main()
