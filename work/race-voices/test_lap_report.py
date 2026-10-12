import unittest
from pathlib import Path
from lupa import LuaRuntime

SCRIPT = Path(__file__).with_name('lap_report.lua')

class LapReportTests(unittest.TestCase):
    def run_lap(self, facts, lap):
        lua = LuaRuntime(unpack_returned_tuples=True)
        spoken = []
        rules = lua.table()
        rules.GetValue = lambda key, default=None: facts.get(key, default)
        rules.SetValue = lambda key, value: facts.update({key: value})
        assistant = lua.table()
        assistant.Speak = lambda text: spoken.append(text)
        lua.globals().Rules = rules
        lua.globals().Assistant = assistant
        lua.globals().Arguments = lua.table_from([lap])
        lua.globals().REPORT_LOG_ROOT = str(Path(__file__).parent/'test-logs')
        lua.execute(SCRIPT.read_text(encoding='utf-8'))
        return spoken

    def test_once_and_best_delta(self):
        f = {'Lap.2.Time': 91234, 'Lap.2.Valid': True}
        self.assertIn('1分31.2秒', self.run_lap(f, 2)[0])
        self.assertEqual([], self.run_lap(f, 2))
        f.update({'Lap.3.Time': 91834, 'Lap.3.Valid': True})
        self.assertIn('慢0.6秒', self.run_lap(f, 3)[0])

    def test_invalid_does_not_set_best(self):
        f = {'Lap.2.Time': 80000, 'Lap.2.Valid': False}
        self.assertIn('无效圈', self.run_lap(f, 2)[0])
        self.assertNotIn('BasicReport.Best', f)

    def test_missing_and_outlap_are_silent(self):
        self.assertEqual([], self.run_lap({}, 1))
        self.assertEqual([], self.run_lap({'Lap.2.Time': 0}, 2))

    def test_first_timed_lap_is_reported(self):
        self.assertIn('1分14.3秒', self.run_lap({'Lap.1.Time': 74282, 'Lap.1.Valid': True}, 1)[0])

if __name__ == '__main__':
    unittest.main()
