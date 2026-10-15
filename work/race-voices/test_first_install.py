"""Exercise installation, integration, range preparation and automatic launch together."""
import json,sys,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import Mock,patch
from install_simulator import prepare_config
import setup_simulator
from simulator_link import SimulatorLink

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'app'))
from simulator_status import inspect_simulator


class FirstInstallTests(unittest.TestCase):
    def test_clean_install_then_integrate_and_start_with_150m_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);sc=base/'controller';docs=base/'documents';app=base/'assistant'
            (sc/'Config').mkdir(parents=True);(sc/'Binaries').mkdir();(app/'config').mkdir(parents=True)
            (sc/'Config/Simulator Configuration.ini').write_text('[Configuration]\nSimulators=\n')
            for name in ('Simulator Startup.exe','Simulator Controller.exe','Voice Server.exe'):(sc/'Binaries'/name).touch()
            prepare_config(sc,docs)
            (app/'config/default.json').write_text(json.dumps({'documents':str(docs),'simulator_controller':str(sc),'port':9881}))
            with patch.object(setup_simulator,'documents',return_value=docs),patch.object(setup_simulator,'settings',return_value={'port':9881}):setup_simulator.main()
            state=inspect_simulator(app)
            self.assertTrue(state['configured']);self.assertTrue(state['integrated'])
            process=Mock();process.pid=123;process.exe.return_value=str(sc/'Binaries/Simulator Controller.exe');process.create_time.return_value=456.
            def launch(*args,**kwargs):
                home=docs/'Simulator Controller'
                identity=(home/'Config/ID').read_text().strip()
                self.assertEqual(uuid.UUID(identity).version,4)
                self.assertEqual((home/'Database/ID').read_text().strip(),identity)
                self.assertIn(identity+';*;*;*;Assistant.Spotter;SlowCar.Distance.Ahead.Threshold;150;*',(home/'Database/User/IRC/Settings.CSV').read_text())
                return process
            link=SimulatorLink(base/'owner.json',lambda:state)
            with patch('simulator_link.running_controller',return_value=None),patch('simulator_link.running_voice_server',return_value=process),patch('simulator_link.psutil.Process',return_value=process),patch('simulator_link.subprocess.Popen',side_effect=launch) as spawn:
                self.assertEqual(link.ensure(True),'started')
                spawn.assert_called_once()
            self.assertEqual(json.loads(link.owner.read_text())['pid'],123)

    def test_upgrade_with_missing_identity_is_initialized_before_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);exe=base/'Binaries/Simulator Controller.exe';exe.parent.mkdir();exe.touch();(exe.parent/'Voice Server.exe').touch()
            docs=base/'documents';state=dict(root=base,documents=docs,installed=True,configured=True,integrated=True)
            process=Mock();process.pid=123;process.exe.return_value=str(exe);process.create_time.return_value=456.
            def launch(*args,**kwargs):
                self.assertTrue((docs/'Simulator Controller/Config/ID').is_file())
                self.assertTrue((docs/'Simulator Controller/Database/User/IRC/Settings.CSV').is_file())
                return process
            with patch('simulator_link.running_controller',return_value=None),patch('simulator_link.running_voice_server',return_value=process),patch('simulator_link.psutil.Process',return_value=process),patch('simulator_link.subprocess.Popen',side_effect=launch):
                self.assertEqual(SimulatorLink(base/'owner.json',lambda:state).ensure(True),'started')


if __name__=='__main__':unittest.main()
