"""SQLite schema for source and derived data."""

SCHEMA_SQL = """
CREATE TABLE projects (
    project_id TEXT PRIMARY KEY CHECK (length(trim(project_id)) > 0)
);

CREATE TABLE subjects (
    subject_id TEXT PRIMARY KEY CHECK (length(trim(subject_id)) > 0),
    project_id TEXT NOT NULL,
    condition TEXT NOT NULL CHECK (length(trim(condition)) > 0),
    age INTEGER NOT NULL CHECK (age >= 0),
    sex TEXT NOT NULL CHECK (sex IN ('F', 'M')),
    treatment TEXT NOT NULL CHECK (length(trim(treatment)) > 0),
    response TEXT CHECK (response IN ('yes', 'no') OR response IS NULL),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE TABLE samples (
    sample_id TEXT PRIMARY KEY CHECK (length(trim(sample_id)) > 0),
    subject_id TEXT NOT NULL,
    sample_type TEXT NOT NULL CHECK (length(trim(sample_type)) > 0),
    time_from_treatment_start INTEGER NOT NULL,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
);

CREATE TABLE populations (
    population_name TEXT PRIMARY KEY CHECK (length(trim(population_name)) > 0)
);

CREATE TABLE cell_counts (
    sample_id TEXT NOT NULL,
    population_name TEXT NOT NULL,
    count INTEGER NOT NULL CHECK (count >= 0),
    PRIMARY KEY (sample_id, population_name),
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
    FOREIGN KEY (population_name) REFERENCES populations(population_name)
);

CREATE INDEX idx_subjects_project ON subjects(project_id);
CREATE INDEX idx_subjects_analysis ON subjects(condition, treatment, response, sex);
CREATE INDEX idx_samples_subject ON samples(subject_id);
CREATE INDEX idx_samples_analysis ON samples(sample_type, time_from_treatment_start);
CREATE INDEX idx_cell_counts_population ON cell_counts(population_name);

CREATE VIEW cell_frequencies AS
WITH sample_totals AS (
    SELECT sample_id, SUM(count) AS total_count
    FROM cell_counts
    GROUP BY sample_id
)
SELECT
    cc.sample_id AS sample,
    st.total_count,
    cc.population_name AS population,
    cc.count,
    100.0 * cc.count / NULLIF(st.total_count, 0) AS percentage
FROM cell_counts AS cc
JOIN sample_totals AS st ON st.sample_id = cc.sample_id;
"""
