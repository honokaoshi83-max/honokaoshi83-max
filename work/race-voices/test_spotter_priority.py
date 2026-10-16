import queue,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import Mock,patch

class SpotterPriorityTests(unittest.TestCase):
    def test_ordinary_speech_does_not_inherit_a_previous_safety_alert(self):
        from opening_sequence import record_component_priority
        from button_priority import active_spotter_safety
        with tempfile.TemporaryDirectory() as tmp,patch('opening_sequence.PRIORITY',Path(tmp)/'priority.json'):
            record_component_priority('左侧有车。',False)
            self.assertTrue(active_spotter_safety())
            record_component_priority('本圈一分零三秒。',False)
            self.assertFalse(active_spotter_safety())

    def test_button_is_received_without_ack_cutting_off_active_sdk_safety(self):
        from telemetry_announcer import Announcer
        a=Announcer.__new__(Announcer);a.items=queue.PriorityQueue();a.status_pending=False
        a.status_lock=threading.Lock();a.status_prompt=Mock();a.safety_active=threading.Event();a.safety_active.set()
        with patch('telemetry_announcer.log'):self.assertTrue(a.submit_status('车辆无告警。'))
        a.status_prompt.play.assert_not_called()
        self.assertTrue(a.items.get_nowait()[-1])

    def test_native_safety_interrupts_a_manual_summary_during_playback(self):
        import io,wave
        from telemetry_announcer import Announcer
        a=Announcer.__new__(Announcer);a.status_lock=threading.Lock();a.status_pending=True
        a.status_ack_until=0;a.error_latched=False;a.items=Mock()
        a.items.get.side_effect=[(-1,(0,0),'车辆无告警。',True),StopIteration]
        stream=io.BytesIO()
        with wave.open(stream,'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\x01\x00'*16000)
        response=Mock(content=stream.getvalue());a.synthesis=Mock();a.synthesis.response.return_value=response
        clock=[0.];played=[]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);flag=root/'Speaking.status'
            def play(path,flags):
                played.append(path)
                if path is not None:flag.touch()
            with patch('telemetry_announcer.ROOT',root),patch('telemetry_announcer.SC_TEMP',root),patch('telemetry_announcer.log') as log,patch('telemetry_announcer.time.monotonic',side_effect=lambda:clock[0]),patch('telemetry_announcer.time.sleep',side_effect=lambda dt:clock.__setitem__(0,clock[0]+dt)),patch('button_priority.active_spotter_safety',return_value=True),patch('winsound.PlaySound',side_effect=play):
                with self.assertRaises(StopIteration):a.play()
            self.assertEqual(len(played),2);self.assertIsNone(played[-1])
            self.assertFalse(a.status_pending)
            self.assertTrue(any(call.args[0]=='yield_to_spotter' for call in log.call_args_list))

    def test_classification_is_limited_to_surrounding_car_safety(self):
        from button_priority import spotter_safety
        for text in ('左侧有车。','右侧还有车。','旁边还有车。','保持线路。','右后方有车。','三车并排。','蓝旗，后方有快车。','后方有GT3组别的快车，保持线路。','两侧已无车。'):
            self.assertTrue(spotter_safety(text),text)
        for text in ('本圈一分零三秒。','车辆无告警。剩余油量二十升。','前一名车手领先五秒。'):
            self.assertFalse(spotter_safety(text),text)

    def test_safety_has_reserved_queue_space_and_precedes_manual(self):
        from button_priority import SpeechQueue
        q=SpeechQueue(capacity=1)
        q.put_nowait((1,(0,0),'普通',False));q.put_nowait((-1,(0,1),'手动',True))
        q.put_nowait((-2,(0,2),'左侧有车。',False))
        self.assertEqual(q.get_nowait()[0],-2)
        self.assertTrue(q.get_nowait()[-1])

    def test_manual_ack_yields_to_active_safety_alert(self):
        from status_prompt import LocalStatusPrompt
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);flag=root/'Speaking.status';flag.touch()
            prompt=LocalStatusPrompt(root/'missing',flag,root,Mock())
            prompt.audio=b'pcm'
            with patch('button_priority.active_spotter_safety',return_value=True):
                self.assertEqual(prompt.play(force=True),0)
            prompt.player.assert_not_called()

    def test_safety_waiting_for_inference_precedes_waiting_manual(self):
        from button_priority import PriorityLock
        lock=PriorityLock();order=[]
        def request(label,**kwargs):
            with lock.hold(**kwargs):order.append(label)
        with lock.hold():
            m=threading.Thread(target=request,args=('manual',),kwargs=dict(manual=True));m.start()
            s=threading.Thread(target=request,args=('safety',),kwargs=dict(safety=True));s.start()
            deadline=time.monotonic()+1
            while getattr(lock,'waiting_safety',0)==0 and time.monotonic()<deadline:time.sleep(.001)
        m.join(1);s.join(1)
        self.assertEqual(order,['safety','manual'])

    def test_safety_http_bypasses_manual_reservation(self):
        from fastapi.testclient import TestClient
        from bridge import create_app
        service=Mock();service.voices={'furina':{},'clorinde':{}};service.speech.return_value=b'ID3-test'
        with tempfile.TemporaryDirectory() as tmp,patch('bridge.ROOT',Path(tmp)),patch('opening_sequence.PRIORITY',Path(tmp)/'priority.json'),patch('button_priority.manual_active',return_value=True),patch('bridge.time.sleep',side_effect=AssertionError('Safety must not wait for manual')):
            response=TestClient(create_app(service)).post('/v1/audio/speech',json=dict(voice='furina',input='左侧有车。',response_format='mp3'))
        self.assertEqual(response.status_code,200)
        self.assertTrue(service.speech.call_args.kwargs.get('safety'))

if __name__=='__main__':unittest.main()
