import concurrent.futures
import tempfile
import time
import unittest
from pathlib import Path

try:
    from bridge import VoiceService
except ImportError:
    VoiceService = None

class VoiceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(VoiceService, 'Local speech adapter is missing')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.calls = []
        def render(voice, text, speed, fmt):
            self.calls.append((voice, text, speed, fmt))
            time.sleep(.01)
            return b'RIFF-test-wave' if fmt == 'wav' else b'ID3-test-mp3'
        self.service = VoiceService(Path(self.tmp.name), render, 'test-model-hash')

    def test_voices_are_independent_and_repeated_phrases_cached(self):
        a = self.service.speech('furina', '油量还能跑五圈。', 1, 'wav')
        self.assertEqual(a, self.service.speech('furina', '油量还能跑五圈。', 1, 'wav'))
        self.service.speech('ganyu', '油量还能跑五圈。', 1, 'wav')
        self.assertEqual(len(self.calls), 2)

    def test_integer_and_float_speed_share_cache(self):
        self.service.speech('clorinde','轮胎检查。',1,'wav')
        self.service.speech('clorinde','轮胎检查。',1.0,'wav')
        self.assertEqual(len(self.calls),1)

    def test_simulator_controller_mp3_format(self):
        self.assertTrue(self.service.speech('clorinde', '准备进站。', 1, 'mp3').startswith(b'ID3'))
        self.assertEqual(self.calls[0][-1], 'mp3')

    def test_engineer_identity_and_cached_intro(self):
        self.service.speech('clorinde', '赛车状态和油量监控已就绪。', 1, 'wav')
        self.assertEqual(self.calls[-1][1], '我是克洛琳德，负责赛车状态、油量和维修提醒。')
        self.service.speech('clorinde', '我是Jona，系统检查完成。', 1, 'wav')
        self.assertIn('克洛琳德', self.calls[-1][1])
        self.assertNotIn('芙宁娜', self.calls[-1][1])

    def test_enabled_pair_excludes_ganyu(self):
        service = VoiceService(Path(self.tmp.name), self.service.render, 'pair', active_voice=('furina','clorinde'))
        self.assertEqual(service.voices, ('furina','clorinde'))
        with self.assertRaises(ValueError):
            service.speech('ganyu', '准备进站。', 1, 'wav')

    def test_concurrent_duplicate_requests_generate_once(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.service.speech('ganyu', '左侧有车。', 1, 'wav'), range(4)))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(set(results)), 1)

    def test_invalid_input_rejected_before_inference(self):
        for args in [('unknown','正常文本',1,'wav'), ('furina','',1,'wav'), ('furina','正常文本',0,'wav'), ('furina','正常文本',1,'exe')]:
            with self.assertRaises(ValueError):
                self.service.speech(*args)
        self.assertEqual(self.calls, [])

    def test_cache_changes_with_model_version(self):
        self.service.speech('furina', '准备进站。', 1, 'wav')
        other = VoiceService(Path(self.tmp.name), self.service.render, 'new-model-hash')
        other.speech('furina', '准备进站。', 1, 'wav')
        self.assertEqual(len(self.calls), 2)

    def test_openai_request_and_invalid_voice_response(self):
        from fastapi.testclient import TestClient
        from bridge import create_app
        client = TestClient(create_app(self.service))
        response = client.post('/v1/audio/speech', json={'model':'gpt-sovits', 'voice':'ganyu', 'input':'左侧有车。', 'response_format':'mp3'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'audio/mpeg')
        self.assertTrue(response.content.startswith(b'ID3'))
        response = client.post('/v1/audio/speech', json={'voice':'unknown', 'input':'左侧有车。'})
        self.assertEqual(response.status_code, 400)

    def test_single_voice_mode_rejects_model_switching(self):
        from fastapi.testclient import TestClient
        from bridge import create_app
        service = VoiceService(Path(self.tmp.name), self.service.render, 'single', active_voice='furina')
        client = TestClient(create_app(service))
        self.assertEqual(client.get('/health').json()['voices'], ['furina'])
        response = client.post('/v1/audio/speech', json={'voice':'ganyu', 'input':'左侧有车。'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.calls, [])

if __name__ == '__main__':
    unittest.main()
