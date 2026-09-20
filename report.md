# Analysis report

This report answers the clinical-trial analysis questions for `cell-count.csv`. The pipeline loads the source file into SQLite, derives cell-population frequencies, runs the responder comparison, and exposes the results in the Streamlit dashboard.

## Data overview

Each source row represents one biological sample. The file contains five immune-cell populations: `b_cell`, `cd8_t_cell`, `cd4_t_cell`, `nk_cell`, and `monocyte`.

The database contains 10,500 samples and 52,500 cell-frequency records. Each sample has five population records. The pipeline calculates each percentage as:

```text
total_count = sum of the five population counts
percentage = population count / total_count * 100
```

The five percentages for each sample sum to 100%.

## Responder analysis

The responder analysis uses melanoma patients treated with miraclib and PBMC samples with a recorded response of `yes` or `no`. It includes 331 responder subjects and 325 non-responder subjects.

The independent unit is the subject. For each subject and population, the pipeline averages the percentages at days 0, 7, and 14. It then compares the two response groups with Welch's two-sample t-test. The report includes the mean difference, a 95% confidence interval, the raw p-value, and the Benjamini-Hochberg adjusted p-value for the five population tests.

| Population | Responder mean | Non-responder mean | Difference | 95% confidence interval | Raw p-value | Adjusted p-value |
|---|---:|---:|---:|---:|---:|---:|
| B cells | 9.7976% | 9.9963% | -0.1988 | -0.4780 to 0.0805 | 0.162718 | 0.274043 |
| CD4 T cells | 30.5378% | 29.9023% | 0.6355 | 0.1976 to 1.0735 | 0.004515 | 0.022575 |
| CD8 T cells | 24.8819% | 24.9439% | -0.0620 | -0.4719 to 0.3479 | 0.766572 | 0.766572 |
| Monocytes | 19.9418% | 20.0843% | -0.1426 | -0.5149 to 0.2298 | 0.452375 | 0.565469 |
| NK cells | 14.8409% | 15.0732% | -0.2322 | -0.5598 to 0.0954 | 0.164426 | 0.274043 |

CD4 T cells are the only population with an adjusted p-value below 0.05. Their responder mean is 0.6355 percentage points higher than the non-responder mean.

This is a subject-level association. It does not establish a treatment effect, and it is not a validated predictor of response for a new patient.

## Baseline subset analysis

The baseline subset uses melanoma PBMC samples from patients treated with miraclib at time 0. It contains 656 samples.

### Samples by project

| Project | Samples |
|---|---:|
| `prj1` | 384 |
| `prj3` | 272 |

There are no matching baseline samples from `prj2`.

### Subjects by response

| Response | Subjects |
|---|---:|
| Responders | 331 |
| Non-responders | 325 |

### Subjects by sex

| Sex | Subjects |
|---|---:|
| Female | 312 |
| Male | 344 |

## Assignment metric

For melanoma male responders at time 0, across all sample and treatment types, the average raw B-cell count is:

```text
10206.15
```

This metric uses `condition = melanoma`, `sex = M`, `response = yes`, `time_from_treatment_start = 0`, and `population = b_cell`. It does not apply a sample-type or treatment filter.

## Limits of the current analysis

- The source dataset is fixed and small.
- The responder analysis is associative rather than causal.
- Averaging days 0, 7, and 14 removes information about individual trajectories.
- The project has no authentication or patient-data access controls.
- SQLite and synchronous analysis fit this assignment, but they are not designed for a distributed, write-heavy service.
