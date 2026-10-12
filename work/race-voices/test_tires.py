import copy
import math
import unittest

class TireTests(unittest.TestCase):
    def sample(self, **kwargs):
        result=dict(active=True,in_stall=False,on_pit_road=False,speed=20,completed_laps=3,
                    tires={w:dict(cold_kpa=180,pressure_kpa=None,carcass_c=[80,80,80],remaining=[1,1,1])
                           for w in ('LF','RF','LR','RR')})
        result.update(kwargs)
        return result

    def fresh(self,monitor,sample,field,value):
        monitor.update(sample,0)
        sample=copy.deepcopy(sample)
        sample.update(in_stall=True,on_pit_road=True,speed=0)
        sample['tires']['LF'][field]=value
        self.assertEqual(monitor.update(sample,1),[])
        return sample,monitor.update(sample,3.1)

    def test_stale_pit_data_never_announced_while_driving(self):
        from tire_monitor import TireMonitor
        m=TireMonitor(); s=self.sample()
        s['tires']['LF'].update(carcass_c=[150]*3,remaining=[.2]*3)
        self.assertEqual(m.update(s,0),[])
        self.assertEqual(m.update(s,100),[])
        s.update(in_stall=True,on_pit_road=True,speed=0)
        self.assertEqual(m.update(s,110),[])
        self.assertEqual(m.update(s,113),[])

    def test_fresh_temperature_warning_and_dedup(self):
        from tire_monitor import TireMonitor
        m=TireMonitor(); s,result=self.fresh(m,self.sample(),'carcass_c',[140,138,135])
        self.assertEqual(len(result),1)
        self.assertIn('胎温',result[0])
        self.assertEqual(m.update(s,10),[])

    def test_low_temperature_requires_completed_warmup_laps(self):
        from tire_monitor import TireMonitor
        for laps,expected in ((0,False),(3,True)):
            s,result=self.fresh(TireMonitor(),self.sample(completed_laps=laps),'carcass_c',[25]*3)
            self.assertEqual(bool(result),expected)

    def test_wear_is_remaining_not_consumed_and_worst_band(self):
        from tire_monitor import TireMonitor
        m=TireMonitor(); s,result=self.fresh(m,self.sample(),'remaining',[.65,.9,.9])
        self.assertEqual(len(result),1)
        self.assertIn('胎纹余量',result[0])
        s['tires']['LF']['remaining']=[.35,.9,.9]
        m.update(s,5)
        self.assertIn('严重磨损',m.update(s,7.1)[0])

    def test_offline_replay_missing_and_invalid_values(self):
        from tire_monitor import TireMonitor
        m=TireMonitor(); s=self.sample(active=False)
        s['tires']['LF'].update(cold_kpa=0,carcass_c=[float('nan')]*3,remaining=[-1,100,float('inf')])
        self.assertEqual(m.update(s,0),[])
        s['active']=True
        self.assertEqual(m.update(s,1),[])
        self.assertEqual(m.update(s,10),[])

    def test_all_zero_uninitialized_wear_is_not_worn_out_tires(self):
        from tire_monitor import TireMonitor
        m=TireMonitor(); s=self.sample(); m.update(s,0)
        s.update(in_stall=True,on_pit_road=True,speed=0)
        s['tires']['LF'].update(carcass_c=[0]*3,remaining=[0]*3)
        m.update(s,1)
        self.assertEqual(m.update(s,3.1),[])

    def test_replay_snapshot_is_disabled(self):
        from tire_monitor import tire_snapshot
        class IR(dict):
            var_headers_names=['IsOnTrack','IsReplayPlaying']
        self.assertFalse(tire_snapshot(IR(IsOnTrack=True,IsReplayPlaying=True))['active'])

    def test_cold_pressure_settings_are_not_live_pressure(self):
        from tire_monitor import TireMonitor
        m=TireMonitor(); s=self.sample()
        s['tires']['LF']['cold_kpa']=90
        self.assertEqual(m.update(s,0),[])
        self.assertIn('冷胎压设置',m.update(s,2.1)[0])
        self.assertFalse(m.status()['capabilities']['measured_pressure'])

    def test_pit_pressure_is_fresh_unit_converted_and_not_dp_target(self):
        from tire_monitor import tire_snapshot
        from types import SimpleNamespace
        class IR(dict):
            var_headers_names=['LFpressure','LFcoldPressure','dpLFTireColdPress','LFwearL','LFtempCL','IsOnTrack']
            _var_headers_dict={'LFpressure':SimpleNamespace(unit='Pa')}
        ir=IR(LFpressure=200000,LFcoldPressure=180,dpLFTireColdPress=90000,LFwearL=.75,LFtempCL=90,IsOnTrack=True)
        s=tire_snapshot(ir)
        self.assertEqual(s['tires']['LF']['pressure_kpa'],200)
        self.assertEqual(s['tires']['LF']['cold_kpa'],180)
        self.assertEqual(s['tires']['LF']['remaining'][0],.75)

    def test_measurement_pressure_missing_unit_is_disabled(self):
        from tire_monitor import tire_snapshot
        class IR(dict):
            var_headers_names=['LFpressure']
        self.assertIsNone(tire_snapshot(IR(LFpressure=180))['tires']['LF']['pressure_kpa'])

    def test_freshness_is_per_wheel_and_per_metric(self):
        from tire_monitor import TireMonitor
        s=self.sample(); s['tires']['RF']['remaining']=[.2]*3
        m=TireMonitor(); s,result=self.fresh(m,s,'carcass_c',[140]*3)
        self.assertEqual(len(result),1)
        self.assertIn('胎温',result[0])
        self.assertNotIn('磨损',''.join(result))

    def test_fresh_pressure_warning(self):
        from tire_monitor import TireMonitor
        s=self.sample(); s['tires']['LF']['pressure_kpa']=200
        _,result=self.fresh(TireMonitor(),s,'pressure_kpa',90)
        self.assertIn('胎压',result[0])
        self.assertNotIn('冷胎压',result[0])

    def test_normal_fresh_wear_rearms_after_replacement(self):
        from tire_monitor import TireMonitor
        m=TireMonitor(); s,result=self.fresh(m,self.sample(),'remaining',[.6]*3)
        self.assertTrue(result)
        s['tires']['LF']['remaining']=[1]*3; m.update(s,5); self.assertEqual(m.update(s,7.1),[])
        s['tires']['LF']['remaining']=[.6]*3; m.update(s,9)
        self.assertTrue(m.update(s,11.1))

    def test_configurable_bounds_and_validation(self):
        from tire_monitor import TireMonitor
        with self.assertRaises(ValueError):
            TireMonitor(dict(temperature_c_min=150,temperature_c_max=100))
        m=TireMonitor(dict(temperature_c_max=160))
        _,result=self.fresh(m,self.sample(),'carcass_c',[140]*3)
        self.assertEqual(result,[])

if __name__=='__main__':
    unittest.main()
