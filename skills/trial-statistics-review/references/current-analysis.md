# Current statistical analysis

The responder cohort contains melanoma patients treated with miraclib and only
PBMC samples with response `yes` or `no`.

For each population, the pipeline averages days 0, 7, and 14 within subject.
It then compares responder and non-responder subject means using Welch's
two-sample t-test. Five p-values are adjusted with Benjamini-Hochberg. The
pipeline reports group sizes, means, medians, mean difference, 95% confidence
interval, raw p-value, adjusted p-value, and significance at 0.05.

This answers a subject-level association question. It does not establish causal
treatment effect or out-of-sample predictive performance.

Consider a longitudinal model when the time trajectory matters, observations
are incomplete or irregular, covariate adjustment is required, or the analysis
will support prospective decisions. Create a separate predictive pipeline when
the output must predict response for unseen subjects.
