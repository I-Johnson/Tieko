"""Small database utilities shared by scripts and the dashboard."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

import pandas as pd

from .config import DATABASE_PATH


@contextmanager
def connect_database() -> Iterator[sqlite3.Connection]:
    """Open SQLite with foreign-key enforcement enabled."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        yield connection


def read_query(query: str, params: tuple[object, ...] = ()) -> pd.DataFrame:
    """Return a SQL query as a DataFrame."""
    with connect_database() as connection:
        return pd.read_sql_query(query, connection, params=params)
