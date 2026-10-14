import unittest,time
from driver_numbers import snapshot,normalize_references
from speech_reading import normalize_reading

class DriverNumberTests(unittest.TestCase):
    def test_current_entry_numbers_not_positions(self):
        rows=[{'CarIdx':0,'CarNumber':'72','UserName':'Me Driver','CarClassID':1},
              {'CarIdx':1,'CarNumber':'11','UserName':'Alice Driver','CarClassID':1},
              {'CarIdx':2,'CarNumber':'1','UserName':'Bob Driver','CarClassID':1}]
        data=snapshot({'Drivers':rows,'DriverCarIdx':0},[2,1,3])
        text=normalize_reading(normalize_references('前一名Alice Driver，后一名BobDriver。',data))
        self.assertNotIn('Alice',text);self.assertNotIn('Bob',text)
        self.assertIn('十一号车',text);self.assertIn('一号车',text)
        self.assertEqual(normalize_references(text,data),text)
    def test_no_stale_session_names_or_fabricated_number(self):
        data={'until':time.time()-1,'aliases':{'alice driver':'11'}}
        self.assertEqual(normalize_references('Alice Driver',data),'Alice Driver')
    def test_duplicate_names_not_guessed(self):
        data=snapshot({'Drivers':[{'CarNumber':'11','UserName':'Same Driver'},
                                  {'CarNumber':'12','UserName':'Same Driver'}]})
        self.assertEqual(normalize_references('Same Driver',data),'该赛车')
