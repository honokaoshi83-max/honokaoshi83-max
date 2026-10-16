import io,queue,tempfile,threading,unittest,wave
from pathlib import Path
from unittest.mock import Mock,patch

class StatusPromptTests(unittest.TestCase):
    def test_only_accepted_summary_plays_prompt(self):
        from telemetry_announcer import Announcer
        a=Announcer.__new__(Announcer);a.items=queue.Queue(maxsize=1)
        a.status_pending=False;a.status_lock=threading.Lock();a.status_prompt=Mock()
        a.status_prompt.play.return_value=3.0
        with patch('telemetry_announcer.log'):
            self.assertTrue(a.submit_status('状态。'))
            self.assertFalse(a.submit_status('状态。'))
        a.status_prompt.play.assert_called_once_with(force=True)
        self.assertEqual(a.status_ack_until,3.0)
    def test_full_queue_does_not_confirm_rejected_request(self):
        from telemetry_announcer import Announcer
        a=Announcer.__new__(Announcer);a.items=queue.Queue(maxsize=1);a.items.put('busy')
        a.status_pending=False;a.status_lock=threading.Lock();a.status_prompt=Mock()
        with patch('telemetry_announcer.log'):self.assertFalse(a.submit_status('状态。'))
        a.status_prompt.play.assert_not_called()
    def test_local_file_playback_and_safety_priority(self):
        from status_prompt import LocalStatusPrompt
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);audio=root/'prompt.wav';flag=root/'Speaking.status'
            with wave.open(str(audio),'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\x01\x00'*16000)
            player=Mock()
            prompt=LocalStatusPrompt(audio,flag,root,player)
            with patch('status_prompt.time.monotonic',return_value=10):self.assertEqual(prompt.play(),11)
            player.assert_called_once()
            flag.touch();player.reset_mock()
            self.assertEqual(prompt.play(),0);player.assert_not_called()
    def test_prompt_is_interrupted_when_native_voice_starts(self):
        from status_prompt import LocalStatusPrompt
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);flag=root/'Speaking.status';player=Mock()
            prompt=LocalStatusPrompt(root/'missing',flag,root,player);flag.touch()
            prompt.monitor(1000000000)
            player.assert_called_once()
            self.assertIsNone(player.call_args.args[0])

    def test_missing_audio_does_not_block_report(self):
        from status_prompt import LocalStatusPrompt
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);player=Mock()
            prompt=LocalStatusPrompt(root/'missing.wav',root/'Speaking.status',root,player)
            self.assertEqual(prompt.play(),0);player.assert_not_called()
    def test_summary_playback_waits_for_prompt(self):
        import io
        from telemetry_announcer import Announcer
        a=Announcer.__new__(Announcer);a.status_lock=threading.Lock();a.status_pending=True
        a.status_ack_until=1.;a.error_latched=False;a.items=Mock()
        a.synthesis=Mock()
        a.synthesis.response.side_effect=lambda key,fetch,preempted,manual=False,safety=False:fetch()
        a.items.get.side_effect=[(0,'状态。',True),StopIteration]
        stream=io.BytesIO()
        with wave.open(stream,'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\x01\x00'*160)
        response=Mock(content=stream.getvalue());clock=[0.];played=[]
        with tempfile.TemporaryDirectory() as d, patch('telemetry_announcer.ROOT',Path(d)),patch('telemetry_announcer.SC_TEMP',Path(d)),patch('telemetry_announcer.log'),patch('telemetry_announcer.time.monotonic',side_effect=lambda:clock[0]),patch('telemetry_announcer.time.sleep',side_effect=lambda dt:clock.__setitem__(0,clock[0]+dt)),patch('requests.post',return_value=response) as api,patch('winsound.PlaySound',side_effect=lambda *args:played.append(clock[0])):
            with self.assertRaises(StopIteration):a.play()
            self.assertTrue(played);self.assertGreaterEqual(played[0],1.)
            api.assert_called_once();self.assertFalse(a.status_pending)

if __name__=='__main__':unittest.main()
