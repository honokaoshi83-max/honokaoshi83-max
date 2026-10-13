import unittest

class StatusButtonTests(unittest.TestCase):
    def test_pending_summary_is_not_queued_twice(self):
        import queue,threading
        from telemetry_announcer import Announcer
        from unittest.mock import patch
        announcer=Announcer.__new__(Announcer)
        announcer.items=queue.Queue(maxsize=8); announcer.status_pending=False
        announcer.status_lock=threading.Lock()
        with patch('telemetry_announcer.log'):
            self.assertTrue(announcer.submit_status('当前状态。'))
            self.assertFalse(announcer.submit_status('当前状态。'))
        self.assertEqual(announcer.items.qsize(),1)

    def test_hold_reconnect_and_cooldown(self):
        from status_button import PressLatch
        latch=PressLatch(cooldown=5)
        self.assertFalse(latch.update(True,0))
        self.assertFalse(latch.update(False,.1))
        self.assertTrue(latch.update(True,.2))
        self.assertFalse(latch.update(True,10))
        latch.update(False,11)
        self.assertTrue(latch.update(True,12))
        latch.update(None,13)
        self.assertFalse(latch.update(True,14))
        latch.update(False,15)
        self.assertFalse(latch.update(True,16))
        latch.update(False,18)
        self.assertTrue(latch.update(True,19))

    def test_unknowns_do_not_claim_healthy_or_invent_plan(self):
        from status_report import status_phrase, FuelHistory
        text=status_phrase({},FuelHistory())
        self.assertIn('油量数据暂不可用',text)
        self.assertIn('车辆告警数据暂不可用',text)
        self.assertNotIn('进站窗口',text)
        self.assertNotIn('车辆正常',text)

    def test_fuel_full_laps_only_and_refuel_resets(self):
        from status_report import FuelHistory
        history=FuelHistory()
        for lap,fuel in [(0,40),(1,38),(2,36),(3,34)]:
            history.update(lap,fuel,80,False)
        self.assertEqual(history.average,2)
        history.update(3,50,80,True)
        self.assertIsNone(history.average)
        history.update(4,48,80,False)
        self.assertIsNone(history.average)

    def test_pit_lap_excluded_and_low_fuel_plan(self):
        from status_report import FuelHistory,status_phrase
        h=FuelHistory()
        for lap,fuel in [(0,20),(1,18),(2,16),(3,14)]:
            h.update(lap,fuel,80,False)
        text=status_phrase({'fuel':3,'warnings':0,'flags':0,'pit_flags':31,'pit_fuel':10,'pit_fuel_unit':'l'},h)
        self.assertIn('建议本圈进站加油',text)
        self.assertIn('加油十升',text)
        self.assertIn('更换四条轮胎',text)
        h.update(3,13.9,80,True); h.update(4,10,80,False)
        self.assertEqual(h.average,2)

    def test_required_repair_and_finish_margin(self):
        from status_report import FuelHistory,status_phrase
        h=FuelHistory()
        for lap,fuel in [(0,50),(1,48),(2,46),(3,44)]:
            h.update(lap,fuel,80,False)
        text=status_phrase({'fuel':20,'warnings':0x80,'flags':0,'required':30,'race':True,'laps_left':4},h)
        self.assertIn('强制维修',text)
        self.assertIn('油量够到终点',text)
        self.assertNotIn('车身',text)
    def test_empty_plan_and_empty_pit_selection_are_omitted(self):
        from status_report import FuelHistory,status_phrase
        text=status_phrase({'fuel':20,'warnings':0,'flags':0,'pit_flags':0},FuelHistory())
        self.assertEqual(text,'车辆无告警。剩余油量二十升。')
        for phrase in ('当前状态','没有策略','样本不足','进站窗口','不加油','不换胎'):
            self.assertNotIn(phrase,text)

    def test_remove_cloud_preserve_local_tts_and_disable_ptt(self):
        from remove_dialogue import transform
        raw='[Conversation Booster]\nGeneric.ServiceKey=private\nRace Engineer.Service=Generic|https://api.deepseek.com|private\n[Agent Booster]\nRace Engineer.Agent=true\n[Voice Control]\nListener=true\nPushToTalk=1Joy25\nPushToTalkMode=Press\n[Plugins]\nRace Engineer=true||listener: Off; synthesizer: OpenAI|http://127.0.0.1:9881|local\n'
        result=transform(raw)
        self.assertNotIn('private',result)
        self.assertNotIn('deepseek',result)
        self.assertIn('http://127.0.0.1:9881',result)
        self.assertIn('PushToTalk=\n',result)
        self.assertIn('Listener=false',result)
        self.assertEqual(transform(result),result)
