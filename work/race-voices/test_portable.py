import json,tempfile,unittest,zipfile
from pathlib import Path

class PortableTests(unittest.TestCase):
    def test_paths_and_port_have_no_original_device_dependency(self):
        from runtime_settings import settings,service_url,project_root
        self.assertIn('data',str(project_root()/'data'))
        self.assertEqual(service_url({'port':18881}),'http://127.0.0.1:18881')
        # User overrides may legitimately contain their own profile path.
        self.assertEqual(json.loads((project_root()/'config/default.json').read_text(encoding='utf-8'))['documents'],'')

    def test_assets_reject_path_escape_and_incomplete_download(self):
        from portable_assets import target_path,verified
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for path in ('../escape','C:/outside','/outside','a/../../outside'):
                with self.assertRaises(ValueError):target_path(root,path)
            p=target_path(root,'models/正常/file.bin');p.parent.mkdir(parents=True);p.write_bytes(b'bad')
            self.assertFalse(verified(p,{'size':3,'sha256':'0'*64}))

    def test_zip_escape_is_rejected_before_any_extraction(self):
        from portable_assets import safe_extract
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);z=root/'bad.zip'
            with zipfile.ZipFile(z,'w') as out:out.writestr('../escape.txt','bad')
            with self.assertRaises(ValueError):safe_extract(z,root/'target')
            self.assertFalse((root/'escape.txt').exists())

    def test_default_install_does_not_require_role_weights(self):
        from doctor import check_assets
        self.assertEqual(check_assets({'engine':'system'}),[])
        self.assertGreater(len(check_assets({'engine':'gpt-sovits'})),0)

    def test_configuration_disables_old_listener_and_preserves_other_plugins(self):
        from setup_simulator import portable_configure
        old='[Plugins]\nOther=true||keep: value\nRace Engineer=false||listener: On; language: en\n[Voice Control]\nListener=true\nPushToTalk=1Joy25\n[Conversation Booster]\nGeneric.ServiceKey=private\n'
        new=portable_configure(old,18881)
        self.assertIn('Other=true||keep: value',new)
        self.assertNotIn('private',new)
        self.assertEqual(new.count('http://127.0.0.1:18881'),3)
        self.assertNotIn('listener: On',new)
        self.assertIn('PushToTalk=\n',new)
        self.assertEqual(portable_configure(new,18881),new)
