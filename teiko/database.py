from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class Database:
    def __init__(self, path: Path): self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys=ON")
        try: yield connection
        finally: connection.close()

    def initialize(self) -> None:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        with self.connect() as connection: connection.executescript(schema)

    def integrity_check(self) -> None:
        with self.connect() as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok": raise RuntimeError(f"SQLite integrity check failed: {result}")
