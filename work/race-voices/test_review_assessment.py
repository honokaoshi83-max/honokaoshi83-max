import unittest
from review_assessment import assess_session

def laps(times,invalid=()):
    return [dict(lap=i+1,seconds=t,valid=i not in invalid) for i,t in enumerate(times)]

class AssessmentTests(unittest.TestCase):
    def test_equal_half_averages_do_not_imply_stable_individual_laps(self):
        result=assess_session(dict(mode='time_trial',laps=laps([63,65,63,65])))
        text=''.join(result['summary'])
        self.assertEqual(result['trend'],'steady')
        self.assertEqual(result['stability'],'insufficient')
        self.assertEqual(result['standard_deviation'],1)
        self.assertIn('前后半段的平均有效圈速接近',text)
        self.assertNotIn('整体节奏保持一致',text)

    def test_race_with_rank_progress_and_faster_second_half(self):
        row=dict(id='a',mode='race',position=6,class_position=2,grid=9,cars=20,position_source='SDK正式结果',laps=laps([102,102,101,100]))
        result=assess_session(row);text=''.join(result['summary'])
        self.assertIn('第六名',text);self.assertIn('提升三位',text);self.assertIn('后半段',text);self.assertIn('快',text)
        self.assertEqual(result['trend'],'faster');self.assertEqual(result['valid_average'],101.25)
    def test_provisional_rank_does_not_claim_finished(self):
        text=''.join(assess_session(dict(mode='race',position=4,laps=[]))['summary'])
        self.assertIn('最后记录',text);self.assertNotIn('第四名完赛',text)
        self.assertIn('数据不足',text);self.assertNotIn('稳定。',text)
    def test_time_trial_never_uses_positions(self):
        result=assess_session(dict(mode='time_trial',position=1,grid=8,laps=laps([100,100,100,100,100])))
        text=''.join(result['summary']);self.assertNotIn('名',text);self.assertNotIn('提升',text)
        self.assertEqual(result['stability'],'good');self.assertEqual(result['longest_valid_streak'],5)
    def test_invalid_time_in_consistency_but_not_valid_average(self):
        result=assess_session(dict(mode='time_trial',laps=laps([100,100,130,None],(2,3))))
        self.assertEqual(result['valid_average'],100);self.assertEqual(result['invalid_laps'],2)
        self.assertGreater(result['standard_deviation'],10);self.assertEqual(result['stability'],'insufficient')
        self.assertIn('先减少犯规',''.join(result['summary']))
    def test_one_lap_does_not_infer_stability(self):
        result=assess_session(dict(mode='race',laps=laps([100])))
        self.assertEqual(result['stability'],'insufficient');self.assertIsNone(result['standard_deviation'])
        self.assertIn('不足',''.join(result['summary']))
    def test_all_invalid_has_no_valid_pace(self):
        result=assess_session(dict(mode='time_trial',laps=laps([100,None],(0,1))))
        self.assertIsNone(result['best_valid']);self.assertIn('没有有效圈速',''.join(result['summary']))
    def test_missing_laps_break_consecutive_streak(self):
        result=assess_session(dict(mode='time_trial',laps=[dict(lap=i,seconds=100,valid=True) for i in (1,2,5,6)]))
        self.assertEqual(result['longest_valid_streak'],2)
    def test_insufficient_trend_and_repeatable_wording(self):
        row=dict(id='same',mode='race',laps=laps([100,101,100]))
        self.assertEqual(assess_session(row),assess_session(row))
        self.assertEqual(assess_session(row)['trend'],'insufficient')
    def test_no_causes_fuel_or_tyre_guesses(self):
        text=''.join(assess_session(dict(mode='race',laps=laps([100,110,120,130])))['summary'])
        for guess in ('疲劳','轮胎','燃油','事故责任','刹车点'):self.assertNotIn(guess,text)
    def test_disqualification_uses_no_finish_rank(self):
        text=''.join(assess_session(dict(mode='race',disqualified=True,position=3,official=True,laps=laps([100,101])))['summary'])
        self.assertIn('取消资格',text);self.assertNotIn('第三名完赛',text)

    def test_identical_invalid_times_do_not_claim_pace_variation(self):
        result=assess_session(dict(mode='time_trial',laps=laps([100,100],(0,1))))
        text=''.join(result['summary'])
        self.assertEqual(result['standard_deviation'],0);self.assertEqual(result['stability'],'insufficient')
        self.assertNotIn('各圈用时存在波动',text)
        self.assertIn('0.00%',text)

    def test_invalid_identical_times_do_not_hide_valid_lap_variation(self):
        result=assess_session(dict(mode='time_trial',laps=laps([99.5,100.5,100,100,100],(2,3,4))))
        text=''.join(result['summary'])
        self.assertNotIn('有效圈数量不足',text)
        self.assertIn('有效计时圈',text)

if __name__=='__main__':unittest.main()
