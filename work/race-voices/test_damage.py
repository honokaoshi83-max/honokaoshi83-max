import unittest
from damage_monitor import DamageMonitor
from telemetry_announcer import clean_phrase


class DamageTests(unittest.TestCase):
    def sample(self, **changes):
        return dict(dict(incidents=0, warnings=0, flags=0, required=0,
                    optional=0, in_stall=False, rpm=3000, speed=20,
                    active=True), **changes)

    def test_only_one_name_across_opening_roles(self):
        texts = ['我是芙宁娜，会帮你留意周围的赛车。',
                 '我是芙宁娜，会帮你留意赛车状态和油量。',
                 '我是芙宁娜，会帮你留意进站策略。']
        result = ''.join(map(clean_phrase, texts))
        self.assertEqual(result.count('芙宁娜'), 1)
        self.assertIn('油量', result)

    def test_offtrack_is_not_damage_and_contact_is_uncertain(self):
        m = DamageMonitor()
        m.update(self.sample(), 0)
        self.assertEqual(m.update(self.sample(incidents=1), 1), [])
        self.assertEqual(m.update(self.sample(incidents=5), 2), [])
        result = m.update(self.sample(incidents=5), 4.1)
        self.assertIn('尚未确认损伤', ''.join(result))
        self.assertEqual(m.update(self.sample(incidents=5), 8), [])

    def test_required_repairs_override_uncertain_contact(self):
        m = DamageMonitor()
        m.update(self.sample(), 0)
        m.update(self.sample(incidents=4, warnings=128), 1)
        result = m.update(self.sample(incidents=4, warnings=128), 3.1)
        self.assertEqual(len(result), 1)
        self.assertIn('强制维修', result[0])
        self.assertIn('返回维修区', result[0])
        self.assertEqual(m.update(self.sample(incidents=4, warnings=128), 20), [])

    def test_optional_escalates_to_required(self):
        m = DamageMonitor()
        m.update(self.sample(warnings=256), 0)
        self.assertIn('可选维修', ''.join(m.update(self.sample(warnings=256), 2.1)))
        m.update(self.sample(warnings=384), 3)
        self.assertIn('强制维修', ''.join(m.update(self.sample(warnings=384), 5.1)))

    def test_engine_warning_does_not_claim_collision_location(self):
        m = DamageMonitor()
        m.update(self.sample(warnings=4), 0)
        result = ''.join(m.update(self.sample(warnings=4), 2.1))
        self.assertIn('机油压力', result)
        self.assertNotIn('受损', result)
        m = DamageMonitor()
        m.update(self.sample(warnings=4, rpm=0, speed=0), 0)
        self.assertEqual(m.update(self.sample(warnings=4, rpm=0, speed=0), 3), [])

    def test_repair_time_only_in_stall_once_and_no_false_all_clear(self):
        m = DamageMonitor()
        m.update(self.sample(required=70), 0)
        self.assertEqual(m.update(self.sample(required=70), 3), [])
        result = m.update(self.sample(required=70, optional=15, in_stall=True), 4)
        self.assertIn('一分十秒', ''.join(result))
        self.assertEqual(m.update(self.sample(required=69, in_stall=True), 5), [])
        self.assertEqual(m.update(self.sample(in_stall=True), 6), [])

    def test_replay_and_out_of_car_are_ignored(self):
        m = DamageMonitor()
        m.update(self.sample(warnings=128, active=False), 0)
        self.assertEqual(m.update(self.sample(warnings=128, active=False), 3), [])

    def test_combined_alerts_use_short_cached_phrases(self):
        m = DamageMonitor()
        m.update(self.sample(warnings=132), 0)
        result = m.update(self.sample(warnings=132), 2.1)
        self.assertEqual(len(result), 2)
        self.assertIn('强制维修', result[0])
        self.assertIn('机油压力', result[1])

    def test_repair_completion_once_after_confirmed_service_end(self):
        m = DamageMonitor()
        m.update(self.sample(required=5, in_stall=True, service_status=1), 0)
        result = m.update(self.sample(in_stall=True, service_status=2), 1)
        self.assertEqual(result, ['本次维修已完成。出站前留意维修区交通，回到赛道后先确认车辆状态。'])
        self.assertEqual(m.update(self.sample(service_status=2), 1.25), [])
        self.assertEqual(m.update(self.sample(in_stall=True, service_status=2), 3), [])

    def test_leaving_early_or_no_repair_does_not_report_completion(self):
        m = DamageMonitor()
        m.update(self.sample(required=5, in_stall=True, service_status=1), 0)
        self.assertEqual(m.update(self.sample(service_status=2), 2), [])
        self.assertEqual(m.update(self.sample(in_stall=True, service_status=2), 3), [])
        self.assertEqual(m.update(self.sample(in_stall=True, service_status=2), 5), [])

    def test_optional_repairs_unfinished_or_missing_values_block_completion(self):
        for changes in [dict(optional=5), dict(required=None), dict(warnings=128), dict(service_status=105)]:
            m = DamageMonitor()
            m.update(self.sample(required=5, in_stall=True, service_status=1), 0)
            values = dict(in_stall=True, service_status=2)
            values.update(changes)
            m.update(self.sample(**values), 1)
            result = m.update(self.sample(**values), 2.1)
            self.assertNotIn('本次维修已完成', ''.join(result))


if __name__ == '__main__':
    unittest.main()
