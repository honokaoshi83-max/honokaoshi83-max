import unittest
from telemetry_announcer import LapTracker, TrackCatalog, clean_phrase
from pathlib import Path

class TelemetryTests(unittest.TestCase):
    def test_track_layout_from_game_identifier(self):
        c = TrackCatalog(Path(__file__).resolve().parents[2]/'data/tracks_zh.json')
        self.assertIn('福斯', c.resolve('oulton fosters', 'Oulton Park Circuit', 'Fosters'))
        self.assertIn('奥尔顿', c.resolve('oulton fosters', 'Oulton Park Circuit', 'Fosters'))
        self.assertEqual('New Track — New Layout', c.resolve('unknown', 'New Track', 'New Layout'))

    def test_grip_is_not_a_track_name(self):
        self.assertEqual('赛道橡胶较少，抓地力偏低。', clean_phrase('赛道是 绿色。'))
        self.assertEqual('赛道抓地状态良好。', clean_phrase('赛道是 Fast。'))

    def test_completed_lap_once_with_timing_delay(self):
        t = LapTracker()
        self.assertIsNone(t.update(0, 0, 0))
        self.assertIsNone(t.update(1, 0, 1))
        self.assertEqual('本圈一分零九秒七。', t.update(1, 69.733, 1.4))
        self.assertIsNone(t.update(1, 69.733, 2))
        self.assertIsNone(t.update(2, 69.733, 3))
        self.assertIn('快0.7秒', t.update(2, 69, 3.2))

    def test_identical_lap_time_and_attach_mid_session(self):
        t = LapTracker()
        self.assertIsNone(t.update(5, 90, 0))
        self.assertIsNone(t.update(6, 90, 1))
        self.assertEqual('本圈一分三十秒零。', t.update(6, 90, 1.6))
        self.assertIsNone(t.update(6, 90, 2))

    def test_reset_and_invalid_lap(self):
        t = LapTracker()
        t.update(0, 0, 0)
        self.assertIn('事故记录', t.update(1, 100, 1, valid=False))
        self.assertIsNone(t.best)
        self.assertIsNone(t.update(0, 0, 2))

    def test_rounding_carries_into_next_minute(self):
        t = LapTracker()
        t.update(0, 0, 0)
        self.assertEqual('本圈一分零零秒零。', t.update(1, 59.96, 1))

    def test_presenter_names_are_unified(self):
        self.assertEqual('我是芙宁娜。', clean_phrase('我是 Elisa。'))
        self.assertEqual('你好，我是芙宁娜。', clean_phrase('你好，我是Jona。'))

if __name__ == '__main__': unittest.main()
