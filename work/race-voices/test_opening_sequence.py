import unittest
from opening_sequence import opening_sequence,native_greeting,ENGINEER,SPOTTER

class OpeningTests(unittest.TestCase):
    def test_silent_component_batch_is_not_urgent_but_hazard_is(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import opening_sequence as module
        with tempfile.TemporaryDirectory() as folder,patch.object(module,'PRIORITY',Path(folder)/'priority.json'):
            module.record_component_priority('赛道干燥。',True)
            self.assertFalse(module.component_interrupts_opening())
            module.record_component_priority('左侧有车。',False)
            self.assertTrue(module.component_interrupts_opening())
            module.record_component_priority('普通状态',False)
            self.assertTrue(module.component_interrupts_opening())
        self.assertTrue(native_greeting('需要帮助随时叫我。'))
    def test_parallel_priority_requests_do_not_collide(self):
        import tempfile,concurrent.futures,json
        from pathlib import Path
        from unittest.mock import patch
        import opening_sequence as module
        with tempfile.TemporaryDirectory() as folder,patch.object(module,'PRIORITY',Path(folder)/'priority.json'):
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda _:module.record_component_priority('普通状态',False),range(16)))
            self.assertFalse(json.loads(module.PRIORITY.read_text())['urgent'])
    def test_order_and_voice_assignment(self):
        lines=opening_sequence('筑波2000',20,32,1)
        self.assertEqual([line.voice for line in lines],['clorinde','clorinde','furina','clorinde','furina','clorinde'])
        self.assertEqual(lines[0],'赛车已经准备就绪。')
        self.assertEqual(lines[1:3],[ENGINEER,SPOTTER])
        self.assertEqual(lines[3],'当前赛道是筑波2000。')
        self.assertEqual(lines[4],'气温20度。赛道温度32度。赛道干燥。')
        self.assertEqual(lines[5],'在比赛中如果想要查询赛车状态请按下通讯按钮，祝你比赛顺利。')
    def test_missing_conditions_are_not_invented(self):
        self.assertEqual(len(opening_sequence('筑波2000',float('nan'),None,0)),5)
    def test_filter_only_native_greetings(self):
        self.assertTrue(native_greeting(ENGINEER))
        self.assertTrue(native_greeting('气温20度，赛道温度32度。晴天。赛道抓地状态：Fast。'))
        self.assertFalse(native_greeting('左侧有车。'))
        self.assertFalse(native_greeting('温度在上升。气温20度，赛道温度32度。'))

    def test_split_state_is_recognized_without_swallowing_hazards(self):
        from opening_sequence import split_opening_state
        self.assertTrue(split_opening_state('气温二十一度，赛道温度二十九度。'))
        self.assertTrue(split_opening_state('赛道橡胶较少，抓地力偏低。'))
        self.assertFalse(split_opening_state('左侧有车。'))
        self.assertFalse(split_opening_state('赛道温度过高，轮胎过热。'))
