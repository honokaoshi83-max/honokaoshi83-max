import json,unittest
from pathlib import Path
from unittest.mock import patch

class UnboundTests(unittest.TestCase):
    def test_fresh_install_has_no_binding(self):
        cfg=json.loads((Path(__file__).parent/'status_button_settings.json').read_text(encoding='utf-8'))
        self.assertIsNone(cfg['device']);self.assertIsNone(cfg['button'])
    def test_unbound_reader_never_opens_device(self):
        from status_button import configured_reader
        with patch('status_button.WinMMButton') as reader:
            self.assertIsNone(configured_reader({'device':None,'button':None}))
            self.assertIsNone(configured_reader({}))
            reader.assert_not_called()
            configured_reader({'device':1,'button':25})
            reader.assert_called_once_with(1,25)

if __name__=='__main__':unittest.main()
