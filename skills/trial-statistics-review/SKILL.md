---
name: trial-statistics-review
description: Design, implement, explain, or review responder analyses for this immune-cell project. Use for hypothesis tests, confidence intervals, longitudinal models, multiplicity, missingness, or predictive-response claims.
---

# Trial statistics review

Judge whether an analysis answers its stated question without overstating the
evidence. Read `analysis.py`, `src/queries.py`, and the statistical tests first.
Use [references/current-analysis.md](references/current-analysis.md) for the
established method and upgrade triggers.

## Start with the claim

Classify the requested output as descriptive, inferential, predictive, or
causal. Do not let a significant association become a claim of prediction or
treatment effect. State the population, outcome, comparison, unit of analysis,
time window, and estimand before choosing a method.

## Review checklist

- Subjects, not repeated samples, must be the independent units unless the model explicitly represents within-subject correlation.
- Check group sizes, missingness, distributions, outliers, and timepoint completeness.
- Report effect size and confidence interval with each p-value.
- Account for multiple population tests with a declared correction strategy.
- For longitudinal questions, evaluate a mixed-effects model or another repeated-measures method instead of automatically averaging timepoints.
- Prespecify covariates, contrasts, subgroup rules, missing-data handling, and sensitivity analyses for confirmatory work.
- For prediction, split data by subject and keep preprocessing inside the validation pipeline. Consider site-held-out or temporal validation when available.
- Report discrimination and calibration for prediction; do not use statistical significance as a performance metric.

## Verification

Use small synthetic datasets with independently calculable expectations. Assert
the numerical result, not only table shape or column presence. Include failure
cases for missing timepoints, empty groups, null results, and data leakage.
Recommend review by a qualified statistician before clinical or regulatory use.
