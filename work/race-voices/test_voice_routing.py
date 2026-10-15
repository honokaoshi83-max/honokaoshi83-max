import unittest
from voice_routing import route_voice
from flag_monitor import FlagMonitor

class RoutingTests(unittest.TestCase):
    def test_checkered_flag_keeps_furina_and_farewell_keeps_clorinde(self):
        flag=FlagMonitor().update(0x1,0)
        self.assertEqual(flag,['方格旗，本次比赛结束，请安全返回。'])
        self.assertEqual(route_voice(flag[0],'clorinde'),'furina')
        self.assertEqual(route_voice('本次比赛结束，期待下一次合作。','furina'),'clorinde')

    def test_interrupted_opening_keeps_its_original_place_after_flag(self):
        import queue,threading
        from unittest.mock import patch
        from telemetry_announcer import Announcer
        from opening_sequence import opening_sequence
        from flag_monitor import FlagLine
        announcer=Announcer.__new__(Announcer)
        announcer.items=queue.PriorityQueue(maxsize=16)
        announcer.urgent_pending=threading.Event()
        lines=opening_sequence('筑波2000',20,30,1)
        with patch('telemetry_announcer.log'),patch('telemetry_announcer.time.monotonic',return_value=100):
            for line in lines:announcer.submit(line)
            interrupted=announcer.items.get()
            announcer.submit(FlagLine('黄旗，前方有危险。'))
            announcer.items.put_nowait(interrupted)
        self.assertEqual(announcer.items.get()[2],'黄旗，前方有危险。')
        self.assertEqual([announcer.items.get()[2] for _ in lines],lines)
    def test_equal_clock_ticks_preserve_complete_opening_order(self):
        import queue,threading
        from unittest.mock import patch
        from telemetry_announcer import Announcer
        from opening_sequence import opening_sequence
        announcer=Announcer.__new__(Announcer)
        announcer.items=queue.PriorityQueue(maxsize=16)
        announcer.urgent_pending=threading.Event()
        lines=opening_sequence('纳瓦拉赛道，高速布局',19,25,1)
        with patch('telemetry_announcer.log'),patch('telemetry_announcer.time.monotonic',return_value=100):
            for line in lines:announcer.submit(line)
        self.assertEqual([announcer.items.get()[2] for _ in lines],lines)
    def test_neutral_preview_keeps_the_selected_voice(self):
        text='这是当前音色的试听，语音播放正常。'
        self.assertEqual(route_voice(text,'furina'),'furina')
        self.assertEqual(route_voice(text,'clorinde'),'clorinde')
    def test_flags_go_before_queued_normal_messages(self):
        import queue,threading
        from unittest.mock import patch
        from telemetry_announcer import Announcer
        from flag_monitor import FlagLine
        announcer=Announcer.__new__(Announcer)
        announcer.items=queue.PriorityQueue(maxsize=16)
        announcer.urgent_pending=threading.Event()
        with patch('telemetry_announcer.log'):
            announcer.submit('本圈一分零九秒七。')
            announcer.submit(FlagLine('黄旗，前方有危险。'))
        self.assertEqual(announcer.items.get()[2],'黄旗，前方有危险。')
        self.assertEqual(announcer.items.get()[2],'本圈一分零九秒七。')
    def test_incorrect_requested_voice_is_overridden(self):
        for text in ('本圈一分零九秒七。','气温二十度。','蓝旗，后方有快车。','前一名十一号车进站。','建议本圈进站。'):
            self.assertEqual(route_voice(text,'clorinde'),'furina')
        for text in ('胎压偏低。','赛车需要强制维修。','剩余油量二十升。','通讯按钮状态摘要。'):
            self.assertEqual(route_voice(text,'furina'),'clorinde')
    def test_flags_only_on_transition_and_black_cause_not_invented(self):
        monitor=FlagMonitor()
        lines=monitor.update(0x10000,0)
        self.assertEqual(len(lines),1);self.assertEqual(lines[0].voice,'furina')
        self.assertIn('查看屏幕',lines[0]);self.assertNotIn('超速',lines[0])
        self.assertEqual(monitor.update(0x10000,10),[])
        self.assertEqual(monitor.update(0,11),[])
        self.assertEqual(monitor.update(0x10000,12),[])
    def test_dq_and_caution_do_not_repeat_generic_flag(self):
        monitor=FlagMonitor()
        lines=monitor.update(0x20000|0x10000|0x4000|0x8,0)
        self.assertEqual(len(lines),2)
        self.assertTrue(any('取消资格' in line for line in lines))
