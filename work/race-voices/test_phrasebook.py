import unittest
from telemetry_announcer import clean_phrase

class PhrasebookTests(unittest.TestCase):
    def test_existing_urgent_calls_are_proofread(self):
        self.assertEqual('右侧有车。', clean_phrase('注意右侧。'))
        self.assertEqual('两侧已无车。', clean_phrase('全部安全。'))

    def test_clear_calls_are_natural_and_keep_the_correct_side(self):
        for before, after in [('左侧清了。', '左侧已无车。'),
                              ('右侧清了。', '右侧已无车。'),
                              ('两侧都清了。', '两侧已无车。'),
                              ('左侧安全。', '左侧已无车。'),
                              ('右侧畅通。', '右侧已无车。')]:
            self.assertEqual(after, clean_phrase(before))
        self.assertEqual('黄旗解除。', clean_phrase('黄旗解除。'))

    def test_dynamic_values_are_preserved(self):
        self.assertEqual('油量偏低，预计还能跑3圈。',
                         clean_phrase('我是Jona，油量仅够3圈，注意控制油耗。'))

    def test_unrelated_text_and_data_are_preserved(self):
        self.assertEqual('维修区限速60公里每小时。', clean_phrase('维修区限速60公里每小时。'))

    def test_native_lap_times_use_tenths_after_seconds(self):
        self.assertEqual('领跑车的圈速是一分零九秒七。',
                         clean_phrase('领跑车当前圈速 1 分 9.73 秒。'))

    def test_shared_weather_template_ignores_file_whitespace(self):
        self.assertEqual('天气目前比较稳定。', clean_phrase('天气会没事的，别担心。'))

if __name__ == '__main__': unittest.main()
