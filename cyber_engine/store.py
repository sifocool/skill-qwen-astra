"""Private transactional state; evidence is content-addressed and checked on read."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Store:
    def __init__(self, directory):
        self.directory = Path(directory).absolute()
        if self.directory.is_symlink():
            raise ValueError("symlink state directory")
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.directory.stat().st_uid != os.getuid():
            raise ValueError("state directory owner")
        self.directory.chmod(0o700)
        path = self.directory / "investigation.sqlite"
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            st = os.fstat(fd)
            if st.st_uid != os.getuid() or st.st_nlink != 1:
                raise ValueError("unsafe state file")
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
        self.db = sqlite3.connect(path, timeout=15)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS evidence (sha TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, ts REAL, name TEXT, sha TEXT, previous TEXT);
        """)

    def close(self):
        self.db.close()

    def load(self):
        row = self.db.execute("SELECT value FROM state WHERE id=1").fetchone()
        if row is None:
            raise ValueError("investigation not initialized")
        value=json.loads(row[0])
        last=self.db.execute("SELECT sha FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        if not last or digest(value)!=last[0]:
            raise ValueError("state integrity mismatch")
        return value

    def save(self, state, event):
        value = canonical(state)
        sha = hashlib.sha256(value.encode()).hexdigest()
        prior = self.db.execute("SELECT sha FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        self.db.execute("INSERT OR REPLACE INTO state VALUES(1,?)", (value,))
        self.db.execute("INSERT INTO events(ts,name,sha,previous) VALUES(?,?,?,?)",
                        (time.time(), event, sha, prior[0] if prior else None))

    def put(self, value):
        sha = digest(value)
        self.db.execute("INSERT OR IGNORE INTO evidence VALUES(?,?)", (sha, canonical(value)))
        return sha

    def get(self, sha):
        row = self.db.execute("SELECT value FROM evidence WHERE sha=?", (sha,)).fetchone()
        if row is None:
            raise ValueError("missing evidence")
        value = json.loads(row[0])
        if digest(value) != sha:
            raise ValueError("corrupted evidence")
        return value
