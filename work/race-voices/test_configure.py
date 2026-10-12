import unittest
try:
    from configure_simulator import configure
except ImportError:
    configure = None

class ConfigurationTests(unittest.TestCase):
    def test_only_three_assistant_voice_settings_change(self):
        self.assertIsNotNone(configure, 'Simulator voice configuration adapter is missing')
        old='[Plugins]\r\nDriving Coach=false||\r\nIRC=true|iRacing|key: {F4}\r\nRace Engineer=true||language: zh; name: Jona; speaker: On; speakerVocalics: 100,*,1; synthesizer: dotNET\r\nRace Spotter=true||speaker: On; synthesizer: dotNET\r\nRace Strategist=true||speaker: On; listener: On\r\n[Other]\r\nUntouched=keep\r\n'
        result = configure(old)
        self.assertIn('Driving Coach=false||\r\nIRC=true|iRacing|key: {F4}', result)
        self.assertIn('name: Jona;', result)
        self.assertIn('[Other]\r\nUntouched=keep', result)
        self.assertEqual(result.count('speaker: gpt-sovits/furina'),2)
        self.assertEqual(result.count('speaker: gpt-sovits/clorinde'),1)
        self.assertEqual(result.count('synthesizer: OpenAI|http://127.0.0.1:9881|local'),3)
        self.assertEqual(configure(result),result)

if __name__ == '__main__':
    unittest.main()
