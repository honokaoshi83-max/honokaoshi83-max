import tempfile
import unittest
from pathlib import Path

class EmotionTests(unittest.TestCase):
    def test_safety_overrides_celebration_and_clear_is_calm(self):
        from emotion_profiles import classify
        self.assertEqual(classify('左侧有车。'), 'warning')
        self.assertEqual(classify('刷新最佳圈，但前方黄旗。'), 'warning')
        self.assertEqual(classify('左侧已无车。'), 'calm')
        self.assertEqual(classify('本圈一分三十秒五。'), 'calm')
        self.assertEqual(classify('刷新个人最佳圈。'), 'encouraging')
        self.assertEqual(classify('本次维修已完成。'), 'calm')
        self.assertEqual(classify('黄旗解除。'), 'calm')
        self.assertEqual(classify('领跑车刷新最快圈。'), 'calm')
        self.assertEqual(classify('发动机水温告警，请减轻负荷。'), 'warning')
        self.assertEqual(classify('冷胎压设置高于当前检查上限，请检查胎压设置。'), 'warning')

    def test_auto_profile_and_explicit_profile_cache_separation(self):
        from bridge import VoiceService
        calls=[]; styles=[]
        with tempfile.TemporaryDirectory() as tmp:
            service=VoiceService(Path(tmp), lambda *args: calls.append(args) or b'raw', 'test',
                style_processor=lambda data, rate: styles.append(rate) or data+b'styled')
            a=service.speech('furina','左侧有车。',1,'wav')
            self.assertEqual(a, service.speech('furina','左侧有车。',1,'wav',emotion='warning'))
            self.assertEqual(service.speech('furina','左侧有车。',1,'wav',emotion='calm'),b'raw')
            self.assertEqual(len(calls),1)
            self.assertEqual(len(styles),1)
            with self.assertRaises(ValueError):
                service.speech('furina','左侧有车。',emotion='angry')

    def test_profile_reference_falls_back_and_content_changes_identity(self):
        from emotion_profiles import resolve
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); base={'reference':'base.wav','reference_text':'正常参考。'}
            cfg={'warning':{'speed':1.04},'voices':{'furina':{'warning':{'reference':'urgent.wav','reference_text':'注意。'}}}}
            fallback=resolve('furina','warning',base,cfg,root)
            self.assertFalse(fallback['reference_ready'])
            (root/'urgent.wav').write_bytes(b'first')
            first=resolve('furina','warning',base,cfg,root)
            self.assertTrue(first['reference_ready'])
            (root/'urgent.wav').write_bytes(b'second')
            self.assertNotEqual(first['identity'],resolve('furina','warning',base,cfg,root)['identity'])

    def test_api_exposes_explicit_emotion_and_rejects_unknown(self):
        from bridge import VoiceService, create_app
        from fastapi.testclient import TestClient
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp,patch('opening_sequence.PRIORITY',Path(tmp)/'priority.json'),patch('bridge.ROOT',Path(tmp)):
            service=VoiceService(Path(tmp),lambda *a:b'RIFF-test', 'test')
            client=TestClient(create_app(service))
            self.assertEqual(client.post('/v1/audio/speech',json={'voice':'furina','input':'正常。','emotion':'calm'}).status_code,200)
            self.assertEqual(client.post('/v1/audio/speech',json={'voice':'furina','input':'正常。','emotion':'angry'}).status_code,400)
