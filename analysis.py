"""Run the clinical-trial analyses and store results in SQLite.

The loader creates the source tables and ``cell_frequencies`` view. This
script reads those database objects, performs the statistical analysis, and
adds result tables used by the dashboard.

Run from any directory with::

    python analysis.py
"""

from __future__ import annotations

import sqlite3

import pandas as pd
from scipy.stats import t, ttest_ind
from statsmodels.stats.multitest import multipletests

from src.config import DATABASE_PATH, POPULATIONS
from src.queries import BASELINE_SQL, FINAL_B_CELL_SQL, RESPONSE_ANALYSIS_SQL


def check_database() -> None:
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}. Run load_data.py first."
        )


def run_responder_analysis(connection: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    """Compare subject-level mean frequencies between response groups.

    Each subject has three observations (days 0, 7, and 14). We first average
    each population's percentage within subject so that subjects, rather than
    time points, are the independent units in the group comparison.
    """
    sample_frequency = pd.read_sql_query(RESPONSE_ANALYSIS_SQL, connection)
    if sample_frequency.empty:
        raise ValueError("The responder analysis filter returned no rows.")

    subject_frequency = (
        sample_frequency.groupby(["subject_id", "response", "population"], as_index=False)
        .agg(
            subject_mean_percentage=("percentage", "mean"),
            timepoint_count=("percentage", "size"),
        )
    )

    expected_timepoints = subject_frequency.loc[
        subject_frequency["timepoint_count"] != 3
    ]
    if not expected_timepoints.empty:
        raise ValueError(
            "Expected three PBMC time points per subject in the responder "
            "analysis; incomplete subjects were found."
        )

    records: list[dict[str, object]] = []
    for population in POPULATIONS:
        current = subject_frequency[subject_frequency["population"] == population]
        responders = current.loc[
            current["response"] == "yes", "subject_mean_percentage"
        ].to_numpy()
        nonresponders = current.loc[
            current["response"] == "no", "subject_mean_percentage"
        ].to_numpy()

        test = ttest_ind(responders, nonresponders, equal_var=False)
        confidence_interval = test.confidence_interval(confidence_level=0.95)
        records.append(
            {
                "population": population,
                "responder_n": int(len(responders)),
                "nonresponder_n": int(len(nonresponders)),
                "responder_mean": float(responders.mean()),
                "nonresponder_mean": float(nonresponders.mean()),
                "responder_median": float(pd.Series(responders).median()),
                "nonresponder_median": float(pd.Series(nonresponders).median()),
                "mean_difference": float(responders.mean() - nonresponders.mean()),
                "p_value": float(test.pvalue),
                "difference_ci_lower": float(confidence_interval.low),
                "difference_ci_upper": float(confidence_interval.high),
            }
        )

    results = pd.DataFrame(records)
    results["adjusted_p_value"] = multipletests(
        results["p_value"], method="fdr_bh"
    )[1]
    results["significant"] = results["adjusted_p_value"] < 0.05
    timepoint_summary = summarize_by_timepoint(sample_frequency)
    change_summary = summarize_change_from_baseline(sample_frequency)

    # Keep the plotting data in long form so Plotly/Streamlit can use it
    # directly without recomputing the subject-level transformation.
    return {
        "response_sample_frequencies": sample_frequency,
        "response_subject_frequencies": subject_frequency,
        "statistical_results": results,
        "response_timepoint_summary": timepoint_summary,
        "response_change_summary": change_summary,
    }


def confidence_interval(
    mean: float, standard_error: float, degrees_of_freedom: int
) -> tuple[float, float]:
    """Return a two-sided 95% t confidence interval."""
    if degrees_of_freedom <= 0 or pd.isna(standard_error):
        return (float("nan"), float("nan"))
    margin = float(t.ppf(0.975, degrees_of_freedom) * standard_error)
    return (mean - margin, mean + margin)


def summarize_by_timepoint(sample_frequency: pd.DataFrame) -> pd.DataFrame:
    """Summarize population percentages at each time point and response."""
    grouped = sample_frequency.groupby(
        ["response", "time_from_treatment_start", "population"]
    )["percentage"]
    summary = grouped.agg(["count", "mean", "median", "std"]).reset_index()
    summary = summary.rename(columns={"count": "n", "std": "standard_deviation"})
    summary["standard_error"] = summary["standard_deviation"] / summary["n"].pow(0.5)
    intervals = summary.apply(
        lambda row: confidence_interval(
            row["mean"], row["standard_error"], int(row["n"] - 1)
        ),
        axis=1,
        result_type="expand",
    )
    summary[["ci_lower", "ci_upper"]] = intervals
    return summary.sort_values(
        ["population", "time_from_treatment_start", "response"]
    ).reset_index(drop=True)


def summarize_change_from_baseline(sample_frequency: pd.DataFrame) -> pd.DataFrame:
    """Summarize within-subject change from day 0 at later time points."""
    subject_values = sample_frequency.pivot_table(
        index=["subject_id", "response", "population"],
        columns="time_from_treatment_start",
        values="percentage",
        aggfunc="mean",
    ).reset_index()
    if 0 not in subject_values.columns:
        raise ValueError("Responder data has no baseline time point (time 0).")

    change_rows: list[pd.DataFrame] = []
    timepoints = sorted(
        column
        for column in subject_values.columns
        if isinstance(column, (int, float)) and column != 0
    )
    for timepoint in timepoints:
        current = subject_values[
            ["subject_id", "response", "population", 0, timepoint]
        ].copy()
        current["time_from_baseline"] = timepoint
        current["change_from_baseline"] = current[timepoint] - current[0]
        change_rows.append(
            current[
                [
                    "subject_id",
                    "response",
                    "population",
                    "time_from_baseline",
                    "change_from_baseline",
                ]
            ]
        )

    changes = pd.concat(change_rows, ignore_index=True)
    grouped = changes.groupby(
        ["response", "time_from_baseline", "population"]
    )["change_from_baseline"]
    summary = grouped.agg(["count", "mean", "median", "std"]).reset_index()
    summary = summary.rename(
        columns={
            "count": "n",
            "mean": "mean_change",
            "median": "median_change",
            "std": "standard_deviation",
        }
    )
    intervals = summary.apply(
        lambda row: confidence_interval(
            row["mean_change"],
            row["standard_deviation"] / row["n"] ** 0.5,
            int(row["n"] - 1),
        ),
        axis=1,
        result_type="expand",
    )
    summary[["ci_lower", "ci_upper"]] = intervals
    return summary.sort_values(
        ["population", "time_from_baseline", "response"]
    ).reset_index(drop=True)


def run_part4_queries(connection: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    """Run and return the required baseline and final-metric SQL queries."""
    baseline_samples = pd.read_sql_query(BASELINE_SQL, connection)
    if baseline_samples.empty:
        raise ValueError("The Part 4 baseline filter returned no rows.")

    samples_by_project = pd.read_sql_query(
        """
        SELECT project_id, COUNT(*) AS sample_count
        FROM (
            SELECT s.sample_id, sub.project_id
            FROM samples AS s
            JOIN subjects AS sub ON sub.subject_id = s.subject_id
            WHERE sub.condition = 'melanoma'
              AND s.sample_type = 'PBMC'
              AND s.time_from_treatment_start = 0
              AND sub.treatment = 'miraclib'
        )
        GROUP BY project_id
        ORDER BY project_id;
        """,
        connection,
    )

    subjects_by_response = pd.read_sql_query(
        """
        SELECT response, COUNT(DISTINCT subject_id) AS subject_count
        FROM (
            SELECT s.subject_id, sub.response
            FROM samples AS s
            JOIN subjects AS sub ON sub.subject_id = s.subject_id
            WHERE sub.condition = 'melanoma'
              AND s.sample_type = 'PBMC'
              AND s.time_from_treatment_start = 0
              AND sub.treatment = 'miraclib'
              AND sub.response IN ('yes', 'no')
        )
        GROUP BY response
        ORDER BY response;
        """,
        connection,
    )

    subjects_by_sex = pd.read_sql_query(
        """
        SELECT sex, COUNT(DISTINCT subject_id) AS subject_count
        FROM (
            SELECT s.subject_id, sub.sex
            FROM samples AS s
            JOIN subjects AS sub ON sub.subject_id = s.subject_id
            WHERE sub.condition = 'melanoma'
              AND s.sample_type = 'PBMC'
              AND s.time_from_treatment_start = 0
              AND sub.treatment = 'miraclib'
        )
        GROUP BY sex
        ORDER BY sex;
        """,
        connection,
    )

    final_b_cell = pd.read_sql_query(FINAL_B_CELL_SQL, connection)

    return {
        "baseline_samples": baseline_samples,
        "baseline_project_counts": samples_by_project,
        "baseline_response_counts": subjects_by_response,
        "baseline_sex_counts": subjects_by_sex,
        "key_metrics": pd.DataFrame(
            [
                {
                    "metric_name": "average_b_cells_melanoma_male_responders_day_0",
                    "metric_value": float(final_b_cell.iloc[0]["average_b_cells"]),
                }
            ]
        ),
    }


def run_data_quality_checks(connection: sqlite3.Connection) -> pd.DataFrame:
    """Run source and derived-table checks and return an audit table."""
    checks: list[dict[str, object]] = []

    def add(name: str, status: str, observed: object, expected: object, details: str) -> None:
        checks.append(
            {
                "check_name": name,
                "status": status,
                "observed_value": str(observed),
                "expected_value": str(expected),
                "details": details,
            }
        )

    expected_counts = {
        "projects": 3,
        "subjects": 3500,
        "samples": 10500,
        "populations": 5,
        "cell_counts": 52500,
        "cell_frequencies": 52500,
    }
    for table, expected in expected_counts.items():
        observed = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        add(
            f"{table}_row_count",
            "PASS" if observed == expected else "FAIL",
            observed,
            expected,
            "Row count matches the supplied dataset contract.",
        )

    foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
    add(
        "foreign_key_integrity",
        "PASS" if not foreign_keys else "FAIL",
        len(foreign_keys),
        0,
        "No orphaned foreign-key records.",
    )
    bad_totals = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT sample, SUM(percentage) AS total_percentage
                FROM cell_frequencies GROUP BY sample
                HAVING ABS(total_percentage - 100.0) > 0.000001
            )
            """
        ).fetchone()[0]
    )
    add(
        "frequency_percentages_sum_to_100",
        "PASS" if bad_totals == 0 else "FAIL",
        bad_totals,
        0,
        "Each sample's five population percentages sum to 100%.",
    )
    null_responses = int(
        connection.execute(
            "SELECT COUNT(*) FROM subjects WHERE response IS NULL"
        ).fetchone()[0]
    )
    add(
        "missing_response_values",
        "INFO" if null_responses else "PASS",
        null_responses,
        0,
        "Missing response values are retained as NULL and excluded from responder tests.",
    )
    incomplete_subjects = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT sub.subject_id
                FROM subjects sub
                JOIN samples s ON s.subject_id = sub.subject_id
                WHERE sub.condition = 'melanoma'
                  AND sub.treatment = 'miraclib'
                  AND s.sample_type = 'PBMC'
                  AND sub.response IN ('yes', 'no')
                GROUP BY sub.subject_id
                HAVING COUNT(DISTINCT s.time_from_treatment_start) != 3
                    OR COUNT(DISTINCT CASE
                        WHEN s.time_from_treatment_start IN (0, 7, 14)
                        THEN s.time_from_treatment_start
                    END) != 3
            )
            """
        ).fetchone()[0]
    )
    add(
        "responder_subject_timepoints",
        "PASS" if incomplete_subjects == 0 else "WARN",
        incomplete_subjects,
        0,
        "Eligible responder subjects have days 0, 7, and 14.",
    )
    return pd.DataFrame(checks)


def store_results(
    connection: sqlite3.Connection,
    responder_results: dict[str, pd.DataFrame],
    part4_results: dict[str, pd.DataFrame],
) -> None:
    """Replace derived result tables while leaving source tables untouched."""
    for table_name, frame in {
        **responder_results,
        **part4_results,
    }.items():
        frame.to_sql(table_name, connection, if_exists="replace", index=False)


def print_report(
    responder_results: dict[str, pd.DataFrame],
    part4_results: dict[str, pd.DataFrame],
    quality_checks: pd.DataFrame,
) -> None:
    stats = responder_results["statistical_results"]
    baseline = part4_results["baseline_samples"]
    metrics = part4_results["key_metrics"]

    print("Analysis complete")
    print(f"  responder-analysis samples: {len(responder_results['response_sample_frequencies']) // 5:,}")
    print(f"  responder-analysis subjects: {stats['responder_n'].iloc[0]:,} responders, {stats['nonresponder_n'].iloc[0]:,} non-responders")
    print(f"  baseline melanoma PBMC/miraclib samples: {len(baseline):,}")
    print("  significant populations after BH correction:")
    significant = stats.loc[stats["significant"], "population"].tolist()
    print(f"    {', '.join(significant) if significant else 'none'}")
    print(
        "  average B cells for melanoma male responders at day 0: "
        f"{metrics.iloc[0]['metric_value']:.2f}"
    )
    print(
        "  data-quality checks: "
        f"{(quality_checks['status'] == 'PASS').sum()} pass, "
        f"{(quality_checks['status'] == 'INFO').sum()} info, "
        f"{quality_checks['status'].isin(['WARN', 'FAIL']).sum()} warn/fail"
    )


def main() -> None:
    check_database()
    with sqlite3.connect(DATABASE_PATH) as connection:
        responder_results = run_responder_analysis(connection)
        part4_results = run_part4_queries(connection)
        quality_checks = run_data_quality_checks(connection)
        store_results(connection, responder_results, part4_results)
        quality_checks.to_sql(
            "data_quality_checks", connection, if_exists="replace", index=False
        )
    print_report(responder_results, part4_results, quality_checks)


if __name__ == "__main__":
    main()
