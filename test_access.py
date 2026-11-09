import hashlib, os, tempfile, unittest
from unittest.mock import patch
from access_control import online_access, AccessDenied

class AccessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        salt = b'1234567890123456'
        digest = hashlib.pbkdf2_hmac('sha256', b'correct-password', salt, 600000).hex()
        self.env = patch.dict(os.environ, {'ACCESS_DB': self.temp.name+'/access.db', 'ONLINE_PASSWORD_HASH':salt.hex()+':'+digest, 'ONLINE_DAILY_LIMIT':'1', 'DEEPSEEK_API_KEY':'fake'})
        self.env.start()
    def tearDown(self):
        self.env.stop(); self.temp.cleanup()
    def test_disabled(self):
        with patch.dict(os.environ, {'ONLINE_PASSWORD_HASH':''}):
            with self.assertRaises(AccessDenied):
                with online_access('anything'): self.fail()
    def test_wrong_password_then_quota(self):
        with self.assertRaises(AccessDenied):
            with online_access('wrong'): self.fail()
        with online_access('correct-password'): pass
        with self.assertRaises(AccessDenied):
            with online_access('correct-password'): self.fail()
    def test_slot_released_after_failure(self):
        with patch.dict(os.environ, {'ONLINE_DAILY_LIMIT':'5'}):
            with self.assertRaises(RuntimeError):
                with online_access('correct-password'): raise RuntimeError()
            with online_access('correct-password'): pass
    def test_global_attempt_limit(self):
        from access_control import _consume
        for _ in range(30): _consume('attempt',30,300)
        with self.assertRaises(AccessDenied):
            with online_access('correct-password'): self.fail()
