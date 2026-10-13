import json,tempfile,unittest
from pathlib import Path
from output_volume import load_volume,apply_volume

class OutputVolumeTests(unittest.TestCase):
    def test_default_bad_and_clamped(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(load_volume(d),100)
            p=Path(d)/'playback_settings.json';p.write_text('{',encoding='utf-8');self.assertEqual(load_volume(d),100)
            p.write_text(json.dumps({'volume_percent':150}),encoding='utf-8');self.assertEqual(load_volume(d),100)
            p.write_text(json.dumps({'volume_percent':-2}),encoding='utf-8');self.assertEqual(load_volume(d),0)
    def test_default_does_not_reencode(self):
        with tempfile.TemporaryDirectory() as d:self.assertEqual(apply_volume(b'original','wav',d,'missing-ffmpeg'),b'original')

if __name__=='__main__':unittest.main()
