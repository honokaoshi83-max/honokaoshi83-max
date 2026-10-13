import json,tempfile,unittest
from pathlib import Path
from voice_library import Catalog,parse_hf

class CatalogTests(unittest.TestCase):
    def setup_catalog(self,d):
        root=Path(d);root.joinpath('voices.json').write_text(json.dumps({key:{'gpt':'models/'+key+'/g.ckpt','sovits':'models/'+key+'/s.pth','reference':'models/'+key+'/r.wav','reference_text':'参考文字','version':'v1'} for key in ('furina','clorinde')}),encoding='utf-8');return Catalog(root)
    def test_defaults_cannot_be_deleted_or_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.setup_catalog(d)
            with self.assertRaises(ValueError):c.delete('furina')
            with self.assertRaises(ValueError):c.delete('clorinde')
            with self.assertRaises(ValueError):c.register('furina',{},'同名')
            self.assertEqual(c.roles(),{'engineer':'clorinde','observer':'furina'})
    def test_delete_selected_reverts_roles_only(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.setup_catalog(d);owned=Path(d)/'models/custom/voice-test';owned.mkdir(parents=True);(owned/'test').write_text('owned')
            c.register('voice-test',{'version':'v1','gpt':'models/custom/voice-test/g.ckpt','sovits':'models/custom/voice-test/s.pth','reference':'models/custom/voice-test/r.wav','reference_text':'你好'},'自定义')
            c.assign('engineer','voice-test');c.assign('observer','voice-test');c.delete('voice-test')
            self.assertEqual(c.roles(),{'engineer':'clorinde','observer':'furina'});self.assertFalse(owned.exists())
    def test_hf_urls_and_reject_other_hosts(self):
        self.assertEqual(parse_hf('https://huggingface.co/User/Model/tree/main/角色'),('User/Model','main','角色'))
        self.assertEqual(parse_hf('User/Model'),('User/Model','main',''))
        for url in ['https://example.com/User/Model','https://huggingface.co/models','User/Model/tree/main/../escape']:
            with self.assertRaises(ValueError):parse_hf(url)

if __name__=='__main__':unittest.main()
