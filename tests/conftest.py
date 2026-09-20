"""Build isolated source databases directly from the supplied CSV."""

import sqlite3

import pytest

from load_data import prepare_tables, read_and_validate_source
from src.schema import SCHEMA_SQL


@pytest.fixture(scope="session")
def source_tables():
    return prepare_tables(read_and_validate_source())


@pytest.fixture
def db(source_tables):
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA_SQL)
    for name, frame in source_tables.items():
        frame.to_sql(name, connection, if_exists="append", index=False)
    try:
        yield connection
    finally:
        connection.close()
