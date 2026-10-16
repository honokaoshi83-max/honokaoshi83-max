import sys,tempfile,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from race_strategy import calculate_plan,save_plan,load_plan

def sample(**overrides):
    row=dict(name='四小时测试',track='纽博格林',car='思域',mode='time',duration_minutes=240,
             race_laps=30,initial_fuel=50,capacity=60,lap_seconds=480,burn=4,reserve_laps=1)
    return dict(row,**overrides)

class StrategyTests(unittest.TestCase):
    def test_four_hours_conservative_finish_and_capacity(self):
        p=calculate_plan(sample())
        self.assertEqual(p['race_laps'],31)
        self.assertEqual(p['stops'],2)
        self.assertEqual(p['first_stop'],11)
        self.assertAlmostEqual(sum(r['add'] for r in p['schedule']),78)
        self.assertTrue(all(r['after']<=60 for r in p['schedule']))
    def test_last_stop_only_adds_required_fuel(self):
        p=calculate_plan(sample(mode='laps',race_laps=20))
        self.assertEqual(p['stops'],1)
        self.assertAlmostEqual(p['schedule'][0]['add'],34)
    def test_enough_fuel_no_stop(self):
        self.assertEqual(calculate_plan(sample(mode='laps',race_laps=10))['stops'],0)
    def test_bad_or_missing_inputs(self):
        for fields in [dict(burn=0),dict(lap_seconds=0),dict(initial_fuel=61),dict(burn=float('nan')),
                       dict(reserve_laps=16),dict(initial_fuel=4),dict(mode='laps',race_laps=1.5),dict(mode='other')]:
            with self.subTest(fields=fields),self.assertRaises(ValueError):calculate_plan(sample(**fields))
    def test_save_reload_and_corrupt_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'config/race-strategy.json';save_plan(path,sample())
            self.assertEqual(load_plan(path),sample())
            path.write_text('{broken',encoding='utf-8')
            with self.assertRaises(ValueError):load_plan(path)

if __name__=='__main__':unittest.main()
