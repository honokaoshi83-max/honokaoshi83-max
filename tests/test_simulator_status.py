import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from simulator_status import inspect_simulator, ROLES

class SimulatorStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); (self.root / 'config').mkdir()
        self.sc = self.root / 'controller'; self.docs = self.root / 'documents'
        (self.root / 'config/local.json').write_text(json.dumps(dict(simulator_controller=str(self.sc), documents=str(self.docs), port=9881)), encoding='utf-8')

    def prepare(self, port=9881, encoding='utf-8'):
        (self.sc / 'Binaries').mkdir(parents=True)
        (self.sc / 'Binaries/Simulator Startup.exe').touch()
        folder = self.docs / 'Simulator Controller/Config'; folder.mkdir(parents=True)
        text = '[Plugins]\nIRC=true|iRacing|\n' + '\n'.join(f'{role}=true||raceAssistant: On; language: zh; listener: Off; speaker: gpt-sovits/furina; synthesizer: OpenAI|http://127.0.0.1:{port}|local' for role in ROLES)
        (folder / 'Simulator Configuration.ini').write_text(text, encoding=encoding)
        folder = self.docs / 'Simulator Controller/Grammars'; folder.mkdir()
        for role in ROLES: (folder / (role + '.grammars.zh')).touch()

    def test_missing_install_has_no_completed_steps(self):
        state = inspect_simulator(self.root)
        self.assertFalse(state['installed']); self.assertFalse(state['configured']); self.assertFalse(state['integrated'])

    def test_utf16_configuration_and_redirected_documents(self):
        self.prepare(encoding='utf-16')
        state = inspect_simulator(self.root)
        self.assertTrue(state['installed']); self.assertTrue(state['configured']); self.assertTrue(state['integrated'])
        self.assertEqual(state['documents'], self.docs)

    def test_wrong_port_needs_reintegration(self):
        self.prepare(port=9882)
        self.assertFalse(inspect_simulator(self.root)['integrated'])

    def test_voice_settings_without_enabled_assistants_are_incomplete(self):
        self.prepare()
        path=self.docs/'Simulator Controller/Config/Simulator Configuration.ini'
        path.write_text(path.read_text().replace('raceAssistant: On; ',''))
        self.assertFalse(inspect_simulator(self.root)['integrated'])

    def test_missing_grammar_needs_reintegration(self):
        self.prepare()
        (self.docs / 'Simulator Controller/Grammars/Race Engineer.grammars.zh').unlink()
        self.assertFalse(inspect_simulator(self.root)['integrated'])

if __name__ == '__main__': unittest.main()
