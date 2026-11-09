"""Server-side password and persistent global quotas for a single app instance."""
import hashlib
import hmac
import os
import sqlite3
import threading
import time
from contextlib import contextmanager, closing
from pathlib import Path

_SLOT = threading.BoundedSemaphore(1)

class AccessDenied(ValueError):
    pass

def _consume(bucket, limit, window):
    path = Path(os.getenv('ACCESS_DB', 'data/access.sqlite3'))
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=10)) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS quota (bucket TEXT PRIMARY KEY, period INTEGER, count INTEGER)')
        db.execute('BEGIN IMMEDIATE')
        period = int(time.time()) // window
        row = db.execute('SELECT period,count FROM quota WHERE bucket=?', (bucket,)).fetchone()
        count = row[1] if row and row[0] == period else 0
        if count >= limit:
            raise AccessDenied('访问次数已达限制，请稍后再试或使用离线分析。')
        db.execute('INSERT OR REPLACE INTO quota VALUES (?,?,?)', (bucket, period, count+1))

def verify(password):
    encoded = os.getenv('ONLINE_PASSWORD_HASH', '')
    if not encoded:
        raise AccessDenied('在线功能尚未启用，请使用离线分析。')
    _consume('attempt', 30, 300)
    try:
        salt, expected = encoded.split(':')
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600000).hex()
    except (ValueError, AttributeError):
        raise AccessDenied('在线密码配置无效。') from None
    if not hmac.compare_digest(actual, expected):
        raise AccessDenied('访问密码错误。')

@contextmanager
def online_access(password):
    verify(password)
    if not (os.getenv('DEEPSEEK_API_KEY') or os.getenv('LLM_API_KEY')):
        raise AccessDenied('在线模型尚未配置。')
    if not _SLOT.acquire(blocking=False):
        raise AccessDenied('在线分析忙碌，请稍后再试。')
    try:
        _consume('daily', int(os.getenv('ONLINE_DAILY_LIMIT', '20')), 86400)
        yield
    finally:
        _SLOT.release()

if __name__ == '__main__':
    import getpass
    password = getpass.getpass('New online access password (at least 12 characters): ')
    if len(password) < 12:
        raise SystemExit('Use at least 12 characters')
    if password != getpass.getpass('Confirm password: '):
        raise SystemExit('Passwords differ')
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600000).hex()
    print('ONLINE_PASSWORD_HASH=' + salt.hex() + ':' + digest)
