import tempfile
import unittest
from pathlib import Path

class RecoveryTests(unittest.TestCase):
    def test_custom_voice_is_not_service_failure(self):
        from unittest.mock import patch,Mock
        import watchdog
        response=Mock();response.json.return_value={'status':'ready','voices':['furina','clorinde','voice-test'],'device':'cpu','instance':watchdog.instance_id()}
        with patch('watchdog.requests.get',return_value=response):self.assertTrue(watchdog.health())
    def test_three_failures_and_backoff(self):
        from watchdog import RecoveryPolicy
        policy = RecoveryPolicy()
        self.assertFalse(policy.due(False, 0))
        self.assertFalse(policy.due(False, 2))
        self.assertTrue(policy.due(False, 4))
        policy.attempted(4)
        self.assertFalse(policy.due(False, 6))
        self.assertTrue(policy.due(False, 9))
        policy.attempted(9)
        self.assertFalse(policy.due(False, 18))
        self.assertTrue(policy.due(False, 19))

    def test_transient_failure_and_stable_recovery(self):
        from watchdog import RecoveryPolicy
        policy = RecoveryPolicy()
        policy.due(False, 0)
        policy.due(True, 2)
        self.assertEqual(policy.failures, 0)
        policy.attempted(2)
        for now in (4,6,8):
            self.assertFalse(policy.due(True, now))
        self.assertEqual(policy.attempts, 0)
        self.assertEqual(policy.next_attempt, 0)

    def test_owned_process_requires_exact_script(self):
        from watchdog import owns_command
        root = Path.cwd()/'work/race-voices'
        self.assertTrue(owns_command(['python', str(root/'bridge.py')], root/'bridge.py'))
        self.assertFalse(owns_command(['python', str(root/'other/bridge.py')], root/'bridge.py'))
        self.assertFalse(owns_command(['python','-c',str(root/'bridge.py')], root/'bridge.py'))

    def test_cache_catalog_uses_user_override_and_deduplicates(self):
        from warm_cache import fixed_phrases
        with tempfile.TemporaryDirectory() as tmp:
            base, user = Path(tmp)/'base', Path(tmp)/'user'
            base.mkdir(); user.mkdir()
            (base/'Race Spotter.grammars.zh').write_text('[Speaker Phrases]\nClearLeft.1=清了\nDynamic.1=剩%laps%圈\n[Commands]\nx=不是语音\n',encoding='utf-8')
            (user/'Race Spotter.grammars.zh').write_text('[Speaker Phrases]\nClearLeft.1=左侧已无车。\nClearLeft.2=左侧已无车。\n[Spotter Phrases]\nRight.1=右侧有车。\n',encoding='utf-8')
            self.assertEqual(fixed_phrases(base,user,'Race Spotter'), ['右侧有车。','左侧已无车。'])

    def test_audio_outage_logged_once_then_rearmed(self):
        from telemetry_announcer import Announcer
        from unittest.mock import patch
        announcer=Announcer.__new__(Announcer)
        announcer.error_latched=False
        with patch('telemetry_announcer.log') as log:
            announcer.audio_state(RuntimeError('offline'))
            announcer.audio_state(RuntimeError('offline'))
            self.assertEqual(log.call_count,1)
            announcer.audio_state()
            self.assertEqual(log.call_args.args[0],'audio_recovered')
            announcer.audio_state(RuntimeError('offline again'))
            self.assertEqual(log.call_count,3)

if __name__ == '__main__':
    unittest.main()
