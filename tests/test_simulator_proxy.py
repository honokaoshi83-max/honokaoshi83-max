import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'work/race-voices'))
from install_simulator import install_portable, safe_extract, prepare_config, enable_iracing, ESSENTIAL

class SimulatorProxyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_downloads_components_before_publishing_installation(self):
        release = self.root / 'release.zip'; component = self.root / 'component.zip'
        with zipfile.ZipFile(release, 'w') as z:
            for name in ESSENTIAL: z.writestr('Simulator Controller/Binaries/' + name, b'MZfixture')
            z.writestr('Simulator Controller/Config/Simulator Configuration.ini', '[Configuration]\nSimulators=\n')
        with zipfile.ZipFile(component, 'w') as z: z.writestr('Setup/test.ini', 'fixture')
        manifest = '[Release]\nVersion=7.2.8.0-release\nDownload=https://example.test/release\nComponents=Configuration->1\n[Components]\nConfiguration.1.Path=Resources\nConfiguration.1.Content=Setup\nConfiguration.1.Download=https://example.test/component\n'
        def download(urls, path):
            shutil.copy2(release if 'release' in urls[0] else component, path)
            return dict(sha256='fixture', url=urls[0])
        target = self.root / 'installed'
        with patch('install_simulator.download_archive', side_effect=download):
            self.assertEqual(install_portable(target, manifest), '7.2.8.0-release')
        self.assertTrue((target / 'Resources/Setup/test.ini').is_file())
        self.assertEqual(len(json.loads((target / 'chinese-assistant-install.json').read_text())['downloads']), 2)
        with self.assertRaises(RuntimeError): install_portable(target, manifest)

    def test_rejects_archive_escape(self):
        archive = self.root / 'unsafe.zip'
        with zipfile.ZipFile(archive, 'w') as z: z.writestr('../escape.txt', 'bad')
        with self.assertRaises(ValueError): safe_extract(archive, self.root / 'extract')
        self.assertFalse((self.root / 'escape.txt').exists())

    def test_new_config_enables_iracing_without_other_simulators(self):
        sc = self.root / 'controller'; (sc / 'Config').mkdir(parents=True)
        (sc / 'Config/Simulator Configuration.ini').write_text('[Configuration]\nSimulators=\n')
        result = prepare_config(sc, self.root / 'documents').read_text(encoding='utf-8-sig')
        self.assertIn('Simulators=iRacing', result); self.assertIn('IRC=true|iRacing|', result)
        identity=self.root/'documents/Simulator Controller/Config/ID'
        self.assertTrue(identity.is_file(),'Fresh installation must create the component identity')
        import uuid
        self.assertEqual(uuid.UUID(identity.read_text()).version,4)
        self.assertEqual(identity.read_bytes(),(self.root/'documents/Simulator Controller/Database/ID').read_bytes())

    def test_existing_controls_are_preserved_and_backed_up(self):
        folder = self.root / 'documents/Simulator Controller/Config'; folder.mkdir(parents=True)
        target = folder / 'Simulator Configuration.ini'
        original = '[Configuration]\nLanguage=en\nSimulators=Assetto Corsa\n[Plugins]\nIRC=false|iRacing|togglePitstopFuelMFD: {F8}\n[Unrelated]\nKeep=original\n'
        target.write_text(original)
        prepare_config(self.root / 'unused-controller', self.root / 'documents')
        result = target.read_text(encoding='utf-8-sig')
        self.assertIn('IRC=true|iRacing|togglePitstopFuelMFD: {F8}', result)
        self.assertIn('Simulators=Assetto Corsa|iRacing', result); self.assertIn('Keep=original', result)
        backups = list(folder.glob('*.bak')); self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), original)
        self.assertEqual(enable_iracing(result), result)

if __name__ == '__main__': unittest.main()
