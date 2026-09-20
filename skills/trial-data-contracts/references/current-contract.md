# Current data contract

## Source grain

One CSV row is one biological sample. The five population columns are raw cell
counts: `b_cell`, `cd8_t_cell`, `cd4_t_cell`, `nk_cell`, and `monocyte`.

## Relational grain

- `projects`: one row per project.
- `subjects`: one row per subject with project and current assignment metadata.
- `samples`: one row per biological sample and timepoint.
- `populations`: one row per supported immune-cell population.
- `cell_counts`: one row per sample and population.
- `cell_frequencies`: derived view at sample-population grain.

`percentage = 100 * population count / total count for the sample`.

## Current cohorts

- Responder analysis: melanoma, miraclib, PBMC, response `yes` or `no`.
- Baseline subset: melanoma, miraclib, PBMC, day 0.
- Final B-cell metric: melanoma, male, responder, day 0, every treatment and sample type.

## Known scale limits

Subject treatment and response are stored as single subject attributes. A real
multi-study system may need separate treatment-assignment and response-assessment
tables with effective dates. Current expected row counts describe the supplied
assignment dataset; they are not universal production constraints.
