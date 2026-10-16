import unittest
from review_assessment import assess_session
from session_review import time_trial_summary

def laps(times,invalid=()):
    return [dict(lap=i+1,seconds=t,valid=i not in invalid) for i,t in enumerate(times)]

class ConsistencyRulesTests(unittest.TestCase):
    def test_speech_and_written_review_do_not_disagree_on_pace_trend(self):
        rows=laps([100,100,100,100.15,100.15,100.15])
        written=assess_session(dict(mode='time_trial',laps=rows))
        spoken=time_trial_summary(rows)
        self.assertEqual(written['trend'],'steady')
        self.assertIn('接近',''.join(spoken['summary']))
        self.assertNotIn('后半段有效圈平均比前半段慢',''.join(spoken['summary']))

    def test_approved_ranges_and_inclusive_boundaries(self):
        from review_consistency import grade
        for cv,expected in [(0,'good'),(.0075,'good'),(.00750001,'medium'),(.02,'medium'),(.02000001,'poor')]:
            self.assertEqual(grade(cv,5),expected)
        self.assertEqual(grade(0,4),'insufficient')

    def test_one_invalid_does_not_automatically_downgrade_equal_pace(self):
        result=assess_session(dict(mode='time_trial',laps=laps([100]*10,(5,))))
        self.assertEqual(result['stability'],'good')
        self.assertEqual(result['invalid_laps'],1)
        self.assertIn('犯规无效圈占', ''.join(result['summary']))

    def test_invalid_slow_lap_remains_in_full_variation(self):
        result=assess_session(dict(mode='time_trial',laps=laps([100]*9+[130],(9,))))
        self.assertEqual(result['stability'],'poor')
        self.assertEqual(result['valid_stability'],'good')
        self.assertGreater(result['variation_ratio'],.02)
        self.assertEqual(result['valid_variation_ratio'],0)

    def test_isolated_slow_lap_is_described_without_erasing_it(self):
        result=assess_session(dict(mode='time_trial',laps=laps([64]*25+[75])))
        text=''.join(result['summary'])
        self.assertEqual(result['timed_laps'],26)
        self.assertEqual(result['slow_outliers'],1)
        self.assertIn('个别圈明显变慢',text)
        self.assertNotIn('持续快慢交替',text)

    def test_short_sample_has_measurement_but_no_rating(self):
        result=assess_session(dict(mode='time_trial',laps=laps([63,65,63,65])))
        self.assertEqual(result['stability'],'insufficient')
        self.assertIn('不足五个计时圈', ''.join(result['summary']))
        self.assertIsNotNone(result['variation_ratio'])

    def test_text_contains_percentage_formula_and_versioned_rules(self):
        result=assess_session(dict(mode='time_trial',laps=laps([99,101]*5)))
        text=''.join(result['summary'])
        self.assertIn('1.00%',text)
        self.assertIn('标准差÷平均圈速',result['evaluation_rule'])
        self.assertIn('圈速有一定波动。（0.75%内为稳定；0.75%至2%为有一定波动；超过2%为不稳定）',text)
        self.assertNotIn('评价规则：',text)
        self.assertIn('0.75%',text);self.assertIn('2%',text)
        self.assertEqual(result['stability'],'medium')
        self.assertEqual(result['consistency_rule'],'cv-075-200-v1')

    def test_short_speech_and_written_review_share_the_rating(self):
        rows=laps([99,101]*5)
        written=assess_session(dict(mode='time_trial',laps=rows))
        spoken=time_trial_summary(rows)
        self.assertEqual(spoken['stability'],written['stability'])
        self.assertEqual(spoken['variation_ratio'],written['variation_ratio'])
        self.assertIn('1.00%', ''.join(spoken['summary']))
        self.assertNotIn('0.75%', ''.join(spoken['summary']))

    def test_missing_invalid_times_still_count_without_fabricating_speed(self):
        result=assess_session(dict(mode='time_trial',laps=laps([100]*5+[None],(5,))))
        self.assertEqual(result['timed_laps'],5)
        self.assertEqual(result['invalid_laps'],1)
        self.assertIn('仅计入犯规比例', ''.join(result['summary']))

if __name__=='__main__':unittest.main()
