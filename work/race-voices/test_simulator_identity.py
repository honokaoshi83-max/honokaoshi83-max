import tempfile,unittest,uuid
from pathlib import Path

try:
    from simulator_identity import ensure_identity
except ImportError:
    ensure_identity=None


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(ensure_identity),'Component identity initialization is missing')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)/'Simulator Controller'

    def put(self,name,text):
        path=self.home/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')
        return path

    def test_new_home_gets_a_persistent_guid_shared_with_database(self):
        value=ensure_identity(self.home)
        self.assertEqual(uuid.UUID(value).version,4)
        paths=[self.home/name for name in ('Config/ID','Database/ID')]
        for path in paths:self.assertEqual(path.read_text(),value)
        stamps=[path.stat().st_mtime_ns for path in paths]
        self.assertEqual(ensure_identity(self.home),value)
        self.assertEqual([path.stat().st_mtime_ns for path in paths],stamps)

    def test_existing_config_identity_is_preserved_byte_for_byte(self):
        path=self.put('Config/ID','existing-user\r\n')
        raw=path.read_bytes();stamp=path.stat().st_mtime_ns
        self.assertEqual(ensure_identity(self.home),'existing-user')
        self.assertEqual(path.read_bytes(),raw);self.assertEqual(path.stat().st_mtime_ns,stamp)
        self.assertEqual((self.home/'Database/ID').read_bytes(),raw)

    def test_existing_database_identity_is_reused_when_config_is_missing(self):
        path=self.put('Database/ID','restored-database')
        raw=path.read_bytes()
        self.assertEqual(ensure_identity(self.home),'restored-database')
        self.assertEqual((self.home/'Config/ID').read_bytes(),raw)
        self.assertEqual(path.read_bytes(),raw)

    def test_existing_distinct_database_owner_is_never_replaced(self):
        self.put('Config/ID','local-user');db=self.put('Database/ID','shared-database-owner')
        stamp=db.stat().st_mtime_ns
        self.assertEqual(ensure_identity(self.home),'local-user')
        self.assertEqual(db.read_text(),'shared-database-owner');self.assertEqual(db.stat().st_mtime_ns,stamp)

    def test_invalid_existing_identity_stops_without_overwriting_it(self):
        for invalid in ('','\n','0','bad;owner','owner\nsecond-owner'):
            with self.subTest(invalid=invalid):
                path=self.put('Config/ID',invalid);raw=path.read_bytes()
                with self.assertRaisesRegex(ValueError,'ID'):ensure_identity(self.home)
                self.assertEqual(path.read_bytes(),raw)
                self.assertFalse((self.home/'Database/ID').exists())


if __name__=='__main__':unittest.main()
