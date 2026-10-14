import unittest
from speech_reading import cardinal,normalize_reading,correct_word,pronunciation_signature

class ReadingTests(unittest.TestCase):
    def test_cardinal_numbers(self):
        for n,result in [(0,'零'),(10,'十'),(101,'一百零一'),(131,'一百三十一'),(2000,'两千'),(1001,'一千零一'),(10000,'一万'),(10001,'一万零一')]:
            self.assertEqual(cardinal(n),result)
    def test_quantity_track_and_decimal(self):
        self.assertEqual(normalize_reading('筑波2000，还可以跑131圈。'), '筑波两千，还可以跑一百三十一圈。')
        self.assertEqual(normalize_reading('加油20.5升，胎压186千帕，温度-2.5度。'),'加油二十点五升，胎压一百八十六千帕，温度负二点五度。')
    def test_year_identifiers_and_existing_spoken_text(self):
        text='二零零九版，64号赛车，BMW M2，版本0.2.3，本圈一分零九秒七。'
        self.assertEqual(normalize_reading(text),text.replace('64号赛车','六十四号赛车'))
        self.assertEqual(normalize_reading('筑波赛道，2000布局，2009版。'),'筑波赛道，两千布局，二零零九版。')
        self.assertEqual(normalize_reading('筑波两千，还可以跑一百三十一圈。'),'筑波两千，还可以跑一百三十一圈。')
    def test_polyphonic_words_are_contextual(self):
        self.assertEqual(correct_word('筑波',['zhu2','bo1']),['zhu4','bo1'])
        self.assertEqual(correct_word('还可以',['huan2','ke3','yi3']),['hai2','ke3','yi3'])
        self.assertEqual(correct_word('归还',['gui1','huan2']),['gui1','huan2'])
        self.assertNotEqual(pronunciation_signature('筑波赛道'),'')
        self.assertEqual(pronunciation_signature('左侧有车。'),'')
