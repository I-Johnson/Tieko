"""Shared configuration and domain constants."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "cell-count.csv"
DATABASE_PATH = ROOT / "cell_counts.db"
TEMP_DATABASE_PATH = ROOT / "cell_counts.tmp.db"

POPULATIONS = [
    "b_cell",
    "cd8_t_cell",
    "cd4_t_cell",
    "nk_cell",
    "monocyte",
]

REQUIRED_COLUMNS = [
    "project",
    "subject",
    "condition",
    "age",
    "sex",
    "treatment",
    "response",
    "sample",
    "sample_type",
    "time_from_treatment_start",
    *POPULATIONS,
]

REQUIRED_TEXT_COLUMNS = [
    "project",
    "subject",
    "condition",
    "sex",
    "treatment",
    "sample",
    "sample_type",
]

SUBJECT_METADATA_COLUMNS = [
    "project",
    "condition",
    "age",
    "sex",
    "treatment",
    "response",
]
