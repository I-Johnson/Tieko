"""Validate cell-count.csv and load it into a normalized SQLite database.

Run this script from any directory with:

    python load_data.py

The database is rebuilt atomically at ``cell_counts.db`` beside this file.
"""

from __future__ import annotations

import sqlite3

import pandas as pd

from src.config import (
    CSV_PATH,
    DATABASE_PATH,
    POPULATIONS,
    REQUIRED_COLUMNS,
    REQUIRED_TEXT_COLUMNS,
    SUBJECT_METADATA_COLUMNS,
    TEMP_DATABASE_PATH,
)
from src.schema import SCHEMA_SQL


def _convert_integer_column(frame: pd.DataFrame, column: str) -> None:
    """Convert a source column to integers and reject missing or decimal values."""
    try:
        numeric = pd.to_numeric(frame[column], errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Column '{column}' contains a non-numeric value.") from exc

    if numeric.isna().any():
        raise ValueError(f"Column '{column}' contains a missing value.")
    if not numeric.mod(1).eq(0).all():
        raise ValueError(f"Column '{column}' must contain whole numbers.")

    frame[column] = numeric.astype("int64")


def read_and_validate_source() -> pd.DataFrame:
    """Read the CSV without changing it and validate fields used by the schema."""
    if not CSV_PATH.is_file():
        raise FileNotFoundError(f"Source file not found: {CSV_PATH}")

    frame = pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False)

    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing_columns:
        raise ValueError(
            "CSV is missing required columns: " + ", ".join(missing_columns)
        )

    frame = frame[REQUIRED_COLUMNS].copy()

    text_columns = [*REQUIRED_TEXT_COLUMNS, "response"]
    for column in text_columns:
        frame[column] = frame[column].str.strip()

    blank_required = {
        column: int(frame[column].eq("").sum())
        for column in REQUIRED_TEXT_COLUMNS
        if frame[column].eq("").any()
    }
    if blank_required:
        details = ", ".join(
            f"{column}={count}" for column, count in blank_required.items()
        )
        raise ValueError(f"Required text fields contain blanks: {details}")

    invalid_responses = sorted(set(frame["response"]) - {"", "yes", "no"})
    if invalid_responses:
        raise ValueError(
            "Column 'response' contains unsupported values: "
            + ", ".join(invalid_responses)
        )

    invalid_sexes = sorted(set(frame["sex"]) - {"F", "M"})
    if invalid_sexes:
        raise ValueError(
            "Column 'sex' contains unsupported values: " + ", ".join(invalid_sexes)
        )

    for column in ["age", "time_from_treatment_start", *POPULATIONS]:
        _convert_integer_column(frame, column)

    if frame["age"].lt(0).any():
        raise ValueError("Column 'age' contains a negative value.")

    negative_counts = [
        population for population in POPULATIONS if frame[population].lt(0).any()
    ]
    if negative_counts:
        raise ValueError(
            "Cell-count columns contain negative values: "
            + ", ".join(negative_counts)
        )

    if frame[POPULATIONS].sum(axis=1).le(0).any():
        raise ValueError("Every sample must have a positive total cell count.")

    duplicate_samples = frame.loc[frame["sample"].duplicated(), "sample"].unique()
    if len(duplicate_samples):
        preview = ", ".join(duplicate_samples[:5])
        raise ValueError(f"Duplicate sample identifiers found: {preview}")

    metadata_variants = frame.groupby("subject", dropna=False)[
        SUBJECT_METADATA_COLUMNS
    ].nunique(dropna=False)
    inconsistent_subjects = metadata_variants.gt(1).any(axis=1)
    if inconsistent_subjects.any():
        preview = ", ".join(metadata_variants.index[inconsistent_subjects][:5])
        raise ValueError(f"Subject metadata is inconsistent for: {preview}")

    # Store missing response values as SQL NULL rather than empty strings.
    frame["response"] = frame["response"].replace("", None)
    return frame


def prepare_tables(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Create normalized tables from the validated, wide source data."""
    projects = (
        frame[["project"]]
        .drop_duplicates()
        .rename(columns={"project": "project_id"})
        .sort_values("project_id")
    )

    subjects = (
        frame[
            [
                "subject",
                "project",
                "condition",
                "age",
                "sex",
                "treatment",
                "response",
            ]
        ]
        .drop_duplicates(subset="subject")
        .rename(columns={"subject": "subject_id", "project": "project_id"})
        .sort_values("subject_id")
    )

    samples = (
        frame[["sample", "subject", "sample_type", "time_from_treatment_start"]]
        .rename(columns={"sample": "sample_id", "subject": "subject_id"})
        .sort_values("sample_id")
    )

    populations = pd.DataFrame({"population_name": POPULATIONS})

    cell_counts = (
        frame[["sample", *POPULATIONS]]
        .melt(
            id_vars="sample",
            value_vars=POPULATIONS,
            var_name="population_name",
            value_name="count",
        )
        .rename(columns={"sample": "sample_id"})
        .sort_values(["sample_id", "population_name"])
    )

    return {
        "projects": projects,
        "subjects": subjects,
        "samples": samples,
        "populations": populations,
        "cell_counts": cell_counts,
    }


def build_database(tables: dict[str, pd.DataFrame]) -> None:
    """Build a temporary database, validate it, then replace the prior output."""
    TEMP_DATABASE_PATH.unlink(missing_ok=True)

    try:
        with sqlite3.connect(TEMP_DATABASE_PATH) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(SCHEMA_SQL)

            for table_name in [
                "projects",
                "subjects",
                "samples",
                "populations",
                "cell_counts",
            ]:
                tables[table_name].to_sql(
                    table_name,
                    connection,
                    if_exists="append",
                    index=False,
                )

            foreign_key_errors = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
            if foreign_key_errors:
                raise RuntimeError(
                    f"Database contains foreign-key errors: {foreign_key_errors[:5]}"
                )

            integrity_result = connection.execute("PRAGMA integrity_check").fetchone()
            if integrity_result != ("ok",):
                raise RuntimeError(f"Database integrity check failed: {integrity_result}")

        TEMP_DATABASE_PATH.replace(DATABASE_PATH)
    except Exception:
        TEMP_DATABASE_PATH.unlink(missing_ok=True)
        raise


def report_database_counts() -> None:
    """Print a concise verification summary after a successful load."""
    objects = [
        "projects",
        "subjects",
        "samples",
        "populations",
        "cell_counts",
        "cell_frequencies",
    ]

    with sqlite3.connect(DATABASE_PATH) as connection:
        counts = {
            name: connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for name in objects
        }

    print(f"Created {DATABASE_PATH.name}")
    for name, count in counts.items():
        print(f"  {name}: {count:,} rows")


def main() -> None:
    frame = read_and_validate_source()
    tables = prepare_tables(frame)
    build_database(tables)
    report_database_counts()


if __name__ == "__main__":
    main()
