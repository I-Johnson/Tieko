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
from scipy.stats import ttest_ind
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
            }
        )

    results = pd.DataFrame(records)
    results["adjusted_p_value"] = multipletests(
        results["p_value"], method="fdr_bh"
    )[1]
    results["significant"] = results["adjusted_p_value"] < 0.05

    # Keep the plotting data in long form so Plotly/Streamlit can use it
    # directly without recomputing the subject-level transformation.
    return {
        "response_sample_frequencies": sample_frequency,
        "response_subject_frequencies": subject_frequency,
        "statistical_results": results,
    }


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


def main() -> None:
    check_database()
    with sqlite3.connect(DATABASE_PATH) as connection:
        responder_results = run_responder_analysis(connection)
        part4_results = run_part4_queries(connection)
        store_results(connection, responder_results, part4_results)
    print_report(responder_results, part4_results)


if __name__ == "__main__":
    main()
