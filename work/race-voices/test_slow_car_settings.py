import tempfile,unittest
from pathlib import Path

try:
    from slow_car_settings import ensure_slow_car_limit
except ImportError:
    ensure_slow_car_limit=None

class SlowCarSettingsTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(ensure_slow_car_limit,'Slow-car configuration adapter is missing')
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)/'Simulator Controller'
        (self.home/'Config').mkdir(parents=True)
        (self.home/'Config/ID').write_text('test-owner',encoding='utf-8')
        self.file=self.home/'Database/User/IRC/Settings.CSV'
        self.file.parent.mkdir(parents=True)

    def test_global_limit_and_repeat_does_not_rewrite_file(self):
        self.file.write_bytes(b'')
        self.assertTrue(ensure_slow_car_limit(self.home))
        text=self.file.read_text(encoding='utf-8-sig')
        self.assertEqual(text.strip(),'test-owner;*;*;*;Assistant.Spotter;SlowCar.Distance.Ahead.Threshold;150;*')
        stamp=self.file.stat().st_mtime_ns
        self.assertTrue(ensure_slow_car_limit(self.home))
        self.assertEqual(self.file.stat().st_mtime_ns,stamp)
        self.assertEqual(len(list(self.file.parent.glob('Settings.CSV.before-slow-car-*.bak'))),1)

    def test_caps_specific_profiles_without_widening_shorter_limit(self):
        untouched='test-owner;*;*;*;Assistant.Spotter;Accident.Distance.Ahead.Threshold;800;*'
        foreign='other-owner;*;*;*;Assistant.Spotter;SlowCar.Distance.Ahead.Threshold;500;*'
        rows=[untouched,foreign,
            'test-owner;M2;Tsukuba;Dry;Assistant.Spotter;SlowCar.Distance.Ahead.Threshold;500;Race',
            'test-owner;TCR;Nurb;Dry;Assistant.Spotter;SlowCar.Distance.Ahead.Threshold;100;Race']
        self.file.write_text('\n'.join(rows)+'\n',encoding='utf-8-sig')
        ensure_slow_car_limit(self.home)
        result=self.file.read_text(encoding='utf-8-sig')
        self.assertIn(untouched,result);self.assertIn(foreign,result)
        self.assertIn('M2;Tsukuba;Dry;Assistant.Spotter;SlowCar.Distance.Ahead.Threshold;150;Race',result)
        self.assertIn('TCR;Nurb;Dry;Assistant.Spotter;SlowCar.Distance.Ahead.Threshold;100;Race',result)

    def test_missing_component_identity_does_not_create_database(self):
        (self.home/'Config/ID').unlink()
        self.assertFalse(ensure_slow_car_limit(self.home))
        self.assertFalse(self.file.exists())

    def test_existing_unicode_identity_is_supported_without_rewriting_it(self):
        identity=self.home/'Config/ID';identity.write_bytes('test-owner'.encode('utf-16'))
        original=identity.read_bytes()
        try:result=ensure_slow_car_limit(self.home)
        except UnicodeError as error:self.fail('Existing component ID encoding must be preserved: '+str(error))
        self.assertTrue(result)
        self.assertEqual(identity.read_bytes(),original)
        self.assertIn('test-owner;*;*;*;Assistant.Spotter;SlowCar.Distance.Ahead.Threshold;150;*',self.file.read_text())

if __name__=='__main__':unittest.main()
