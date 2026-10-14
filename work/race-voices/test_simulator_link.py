import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch

class LinkTests(unittest.TestCase):
    def setup_link(self,folder):
        from simulator_link import SimulatorLink
        executable=Path(folder)/'Binaries/Simulator Controller.exe';executable.parent.mkdir();executable.touch();(executable.parent/"Voice Server.exe").touch()
        state=dict(root=Path(folder),installed=True,configured=True,integrated=True)
        return SimulatorLink(Path(folder)/'owner.json',lambda:state),executable
    def test_waits_for_ready_voice_and_preserves_manual_instance(self):
        with tempfile.TemporaryDirectory() as d:
            link,exe=self.setup_link(d)
            with patch('simulator_link.running_controller',return_value=Mock()),patch('simulator_link.subprocess.Popen') as launch:
                self.assertEqual(link.ensure(False),'waiting_for_voice')
                self.assertEqual(link.ensure(True),'running_manual')
                launch.assert_not_called();self.assertFalse(link.owner.exists())
    def test_launches_once_and_records_exact_process_identity(self):
        with tempfile.TemporaryDirectory() as d:
            link,exe=self.setup_link(d);process=Mock();process.pid=123;process.exe.return_value=str(exe);process.create_time.return_value=456.
            with patch('simulator_link.running_controller',return_value=None),patch('simulator_link.subprocess.Popen',return_value=process) as launch,patch('simulator_link.psutil.Process',return_value=process),patch('simulator_link.running_voice_server',return_value=process):
                self.assertEqual(link.ensure(True),'started')
                self.assertEqual(json.loads(link.owner.read_text())['created'],456.)
            with patch('simulator_link.running_controller',return_value=process),patch('simulator_link.running_voice_server',return_value=process):
                self.assertEqual(link.ensure(True),'running_owned')
            launch.assert_called_once()
            self.assertEqual(launch.call_args.args[0],[str(exe),'-Voice','123'])
    def test_broker_starts_before_controller_and_owned_broker_stops(self):
        with tempfile.TemporaryDirectory() as d:
            link,exe=self.setup_link(d)
            broker=Mock();broker.pid=111;broker.exe.return_value=str(exe.parent/'Voice Server.exe');broker.create_time.return_value=1.
            controller=Mock();controller.pid=222;controller.exe.return_value=str(exe);controller.create_time.return_value=2.;controller.children.return_value=[]
            with patch('simulator_link.running_controller',return_value=None),patch('simulator_link.running_voice_server',return_value=None),patch('simulator_link.time.sleep'),patch('simulator_link.subprocess.Popen',side_effect=[broker,controller]) as launch,patch('simulator_link.psutil.Process',side_effect=[broker,controller]):
                self.assertEqual(link.ensure(True),'started')
                self.assertEqual(launch.call_args_list[0].args[0],[str(exe.parent/'Voice Server.exe')])
                self.assertEqual(launch.call_args_list[1].args[0],[str(exe),'-Voice','111'])
            with patch('simulator_link.psutil.Process',side_effect=[controller,broker]):self.assertEqual(link.stop(),'stopped')
            broker.terminate.assert_called_once();controller.terminate.assert_called_once()

    def test_missing_controller_still_cleans_owned_broker(self):
        import psutil
        with tempfile.TemporaryDirectory() as d:
            link,exe=self.setup_link(d)
            broker=Mock();broker.pid=222;broker.exe.return_value=str(exe.parent/'Voice Server.exe');broker.create_time.return_value=2.
            link.owner.write_text(json.dumps(dict(pid=111,exe=str(exe),created=1.,voice_server=dict(pid=222,exe=broker.exe(),created=2.))))
            with patch('simulator_link.psutil.Process',side_effect=[psutil.NoSuchProcess(111),broker]):self.assertEqual(link.stop(),'stopped')
            broker.terminate.assert_called_once()

    def test_reused_pid_is_never_stopped(self):
        with tempfile.TemporaryDirectory() as d:
            link,exe=self.setup_link(d);link.owner.write_text(json.dumps(dict(pid=123,exe=str(exe),created=456.)))
            process=Mock();process.pid=123;process.exe.return_value=str(exe);process.create_time.return_value=999.
            with patch('simulator_link.psutil.Process',return_value=process):self.assertEqual(link.stop(),'not_owned')
            process.terminate.assert_not_called()
    def test_stop_only_owns_controller_and_its_binary_children(self):
        with tempfile.TemporaryDirectory() as d:
            link,exe=self.setup_link(d);link.owner.write_text(json.dumps(dict(pid=123,exe=str(exe),created=456.)))
            process=Mock();process.pid=123;process.exe.return_value=str(exe);process.create_time.return_value=456.
            child=Mock();child.exe.return_value=str(exe.parent/'Race Engineer.exe')
            foreign=Mock();foreign.exe.return_value=str(Path(d)/'Other.exe')
            process.children.return_value=[child,foreign]
            with patch('simulator_link.psutil.Process',return_value=process):self.assertEqual(link.stop(),'stopped')
            child.terminate.assert_called_once();process.terminate.assert_called_once();foreign.terminate.assert_not_called()

if __name__=='__main__':unittest.main()
