"""Named SQL queries used by the analytical pipeline."""

RESPONSE_ANALYSIS_SQL = """
SELECT f.sample, f.population, f.percentage, s.subject_id,
       s.sample_type, s.time_from_treatment_start, sub.project_id,
       sub.condition, sub.treatment, sub.response, sub.sex
FROM cell_frequencies AS f
JOIN samples AS s ON s.sample_id = f.sample
JOIN subjects AS sub ON sub.subject_id = s.subject_id
WHERE sub.condition = 'melanoma'
  AND sub.treatment = 'miraclib'
  AND s.sample_type = 'PBMC'
  AND sub.response IN ('yes', 'no')
ORDER BY f.sample, f.population;
"""

BASELINE_SQL = """
SELECT s.sample_id, s.subject_id, s.sample_type,
       s.time_from_treatment_start, sub.project_id, sub.condition,
       sub.treatment, sub.response, sub.sex, sub.age
FROM samples AS s
JOIN subjects AS sub ON sub.subject_id = s.subject_id
WHERE sub.condition = 'melanoma'
  AND s.sample_type = 'PBMC'
  AND s.time_from_treatment_start = 0
  AND sub.treatment = 'miraclib'
ORDER BY s.sample_id;
"""

FINAL_B_CELL_SQL = """
SELECT ROUND(AVG(cc.count), 2) AS average_b_cells
FROM samples AS s
JOIN subjects AS sub ON sub.subject_id = s.subject_id
JOIN cell_counts AS cc ON cc.sample_id = s.sample_id
WHERE sub.condition = 'melanoma'
  AND sub.sex = 'M'
  AND sub.response = 'yes'
  AND s.time_from_treatment_start = 0
  AND cc.population_name = 'b_cell';
"""
