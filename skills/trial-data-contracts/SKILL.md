---
name: trial-data-contracts
description: Review or change this project's CSV ingestion, SQLite schema, cohort queries, identifiers, validation, provenance, or database migrations. Use for data-model and pipeline work; do not use for purely visual dashboard edits.
---

# Trial data contracts

Protect the meaning and reproducibility of the clinical-trial data pipeline.

## Establish context

Read `src/config.py`, `src/schema.py`, `load_data.py`, `src/queries.py`, and the
relevant tests before proposing changes. Treat `cell-count.csv` as immutable
source data. Distinguish fixture-specific expectations, such as current row
counts, from rules that should apply to future datasets.

Read [references/current-contract.md](references/current-contract.md) when a
change affects fields, relationships, cohort membership, or computed frequency.

## Required reasoning

- State the grain of every affected table or dataframe.
- Identify primary keys, foreign keys, units, nullable fields, and controlled values.
- Trace each derived value back to source fields and transformations.
- Make ingestion idempotent and atomic. A failure must not replace a valid database with a partial one.
- Validate at the system boundary and produce errors that identify the field and failure.
- Keep cohort filters centralized and test exact inclusion and exclusion behavior.
- Preserve subject independence when repeated samples exist.

## Scaling decisions

Add provenance before adding orchestration: source checksum, schema version,
ingestion timestamp, pipeline version, and dataset version. Introduce migrations
before deployed databases can outlive a single pipeline run. Recommend
PostgreSQL only when concurrent writers, multiple app instances, or network
access justify it; recommend object storage and Parquet when immutable files or
columnar analytical scans become material.

## Verification

Use isolated temporary or in-memory databases. Verify keys and foreign keys,
expected population coverage, percentage totals, null handling, exact
timepoints, duplicate rejection, atomic replacement, and deterministic output.
Run `make test`; run `make pipeline` from a clean copy for release-level changes.
