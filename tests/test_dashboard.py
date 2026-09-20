"""Exercise startup against current, missing, and older databases."""

import sqlite3

import pytest
from streamlit.testing.v1 import AppTest

import analysis as analysis_module
import load_data as load_data_module
from analysis import run_data_quality_checks, run_part4_queries, run_responder_analysis, store_results
from src import config, database


@pytest.mark.parametrize("missing", [
    (),
    ("data_quality_checks",),
    ("response_timepoint_summary",),
    ("response_change_summary",),
    ("data_quality_checks", "response_timepoint_summary", "response_change_summary"),
])
def test_dashboard_handles_database_versions(db, tmp_path, monkeypatch, missing):
    store_results(db, run_responder_analysis(db), run_part4_queries(db))
    run_data_quality_checks(db).to_sql("data_quality_checks", db, index=False)
    for table in missing:
        db.execute(f'DROP TABLE "{table}"')
    db.commit()
    path = tmp_path / "dashboard.db"
    temp_path = tmp_path / "dashboard.tmp.db"
    with sqlite3.connect(path) as destination:
        db.backup(destination)
    monkeypatch.setattr(config, "DATABASE_PATH", path)
    monkeypatch.setattr(config, "TEMP_DATABASE_PATH", temp_path)
    monkeypatch.setattr(database, "DATABASE_PATH", path)
    monkeypatch.setattr(analysis_module, "DATABASE_PATH", path)
    monkeypatch.setattr(load_data_module, "DATABASE_PATH", path)
    monkeypatch.setattr(load_data_module, "TEMP_DATABASE_PATH", temp_path)

    app = AppTest.from_file(str(config.ROOT / "dashboard.py")).run(timeout=30)
    assert not app.exception
    assert not app.error
    assert len(app.tabs) == 3
    assert path.exists()


def test_dashboard_handles_missing_database(tmp_path, monkeypatch):
    path = tmp_path / "missing.db"
    temp_path = tmp_path / "missing.tmp.db"
    monkeypatch.setattr(config, "DATABASE_PATH", path)
    monkeypatch.setattr(config, "TEMP_DATABASE_PATH", temp_path)
    monkeypatch.setattr(database, "DATABASE_PATH", path)
    monkeypatch.setattr(analysis_module, "DATABASE_PATH", path)
    monkeypatch.setattr(load_data_module, "DATABASE_PATH", path)
    monkeypatch.setattr(load_data_module, "TEMP_DATABASE_PATH", temp_path)
    app = AppTest.from_file(str(config.ROOT / "dashboard.py")).run(timeout=30)
    assert not app.exception
    assert not app.error
    assert len(app.tabs) == 3
    assert path.exists()
