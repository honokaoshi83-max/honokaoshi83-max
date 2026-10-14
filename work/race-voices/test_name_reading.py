import json,re,unittest
from runtime_settings import data_path
from name_reading import normalize_names,resolve_car
from speech_reading import correct_word

class NameReadingTests(unittest.TestCase):
    def test_all_catalog_entries_have_explicit_speech(self):
        for file,field in [('tracks_zh.json','tracks'),('cars_zh.json','cars')]:
            rows=json.loads(data_path(file).read_text(encoding='utf-8'))[field]
            for row in rows:
                with self.subTest(name=row['en']):
                    self.assertTrue(row['spoken'])
                    self.assertIsNone(re.search('[A-Za-z0-9]',row['spoken']))
    def test_official_inventory_is_covered(self):
        snapshot=json.loads(data_path('name_catalog_sources.json').read_text(encoding='utf-8'))
        for kind,file,field in [('cars','cars_zh.json','cars'),('tracks','tracks_zh.json','tracks')]:
            rows=json.loads(data_path(file).read_text(encoding='utf-8'))[field]
            paths={p.casefold() for r in rows for p in [r['path'],*r.get('path_aliases',[])]}
            self.assertFalse({r['path'].casefold() for r in snapshot[kind]['rows']}-paths)
    def test_car_model_numbers_and_letters(self):
        self.assertEqual(normalize_names('Porsche 911 GT3 R (992)'), '保时捷九幺幺吉提三阿尔，九九二')
        self.assertEqual(normalize_names('BMW M2 Racing (G87)'), '宝马艾姆二赛车版，吉八七')
        self.assertEqual(resolve_car('bmwm2g87','unknown'),'宝马 M2 赛车版，G87')
        self.assertEqual(normalize_names('筑波赛道，2000布局，完整布局'),'筑波赛道，两千布局，完整布局')
    def test_one_in_all_model_identifiers_uses_yao(self):
        from name_reading import spell_name
        from speech_reading import normalize_reading
        self.assertEqual(normalize_names('保时捷七一八'),'保时捷七幺八')
        self.assertEqual(normalize_reading('一三一号车，车号一一。'),'一百三十一号车，车号十一。')
        self.assertIn('七幺八',normalize_names('Porsche 718 Cayman GT4 Clubsport MR'))
        self.assertIn('艾弗幺五零',normalize_names('NASCAR Truck Ford F150'))
        self.assertIn('零幺',normalize_names('Dallara iR-01'))
        self.assertEqual(normalize_reading('131号车，车号：11，剩余131圈。'),'一百三十一号车，车号：十一，剩余一百三十一圈。')
        self.assertEqual(spell_name('宝马 M1，2018版'),'宝马艾姆幺，二零一八版')
        self.assertIn('一九三四款',spell_name('福特 1934款 双门轿跑'))
        self.assertIn('两千',spell_name('Indy Pro 2000 PM-18'))
        self.assertEqual(normalize_reading('1号弯，1号维修位。'),'1号弯，1号维修位。')

    def test_current_public_model_variants_are_not_truncated(self):
        self.assertEqual(normalize_names('BMW M4 GT3 EVO'),'宝马艾姆四吉提三升级版')
        self.assertNotIn('RS',normalize_names('Audi RS 3 LMS TCR'))

    def test_porsche_911_family_uses_yao(self):
        for text in ('保时捷911','保时捷 911','保时捷九一一','Porsche 911'):
            self.assertEqual(normalize_names(text),'保时捷九幺幺')
        self.assertEqual(normalize_names('911号赛车'),'911号赛车')

    def test_names_do_not_consume_adjacent_identifiers(self):
        self.assertEqual(normalize_names('BMW M2 RacingX'),'BMW M2 RacingX')
    def test_explicit_name_pronunciations(self):
        self.assertEqual(correct_word('勒芒赛道',['lei1','mang2','sai4','dao4']),['le4','mang2','sai4','dao4'])
        self.assertEqual(correct_word('雪佛兰',['xue3','fu2','lan2']),['xue3','fo2','lan2'])
