"""Regression tests for the clinical-trial data pipeline."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from analysis import (
    run_data_quality_checks,
    run_part4_queries,
    run_responder_analysis,
)
from src.config import POPULATIONS
from src.queries import RESPONSE_ANALYSIS_SQL


def test_database_contract_counts(db) -> None:
    assert db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 3
    assert db.execute("SELECT COUNT(*) FROM subjects").fetchone()[0] == 3500
    assert db.execute("SELECT COUNT(*) FROM samples").fetchone()[0] == 10500
    assert db.execute("SELECT COUNT(*) FROM populations").fetchone()[0] == 5
    assert db.execute("SELECT COUNT(*) FROM cell_counts").fetchone()[0] == 52500


def test_frequency_view_has_five_populations_and_sums_to_100(db) -> None:
    population_count = db.execute(
        "SELECT COUNT(DISTINCT population) FROM cell_frequencies"
    ).fetchone()[0]
    bad_samples = db.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT sample, COUNT(*) AS population_count,
                   SUM(percentage) AS percentage_total
            FROM cell_frequencies
            GROUP BY sample
            HAVING population_count != 5
                OR ABS(percentage_total - 100.0) > 0.000001
        )
        """
    ).fetchone()[0]
    assert population_count == len(POPULATIONS)
    assert bad_samples == 0


def test_part4_expected_results(db) -> None:
    results = run_part4_queries(db)

    assert len(results["baseline_samples"]) == 656
    assert results["baseline_project_counts"].set_index("project_id")["sample_count"].to_dict() == {
        "prj1": 384,
        "prj3": 272,
    }
    assert results["baseline_response_counts"].set_index("response")["subject_count"].to_dict() == {
        "no": 325,
        "yes": 331,
    }
    assert results["baseline_sex_counts"].set_index("sex")["subject_count"].to_dict() == {
        "F": 312,
        "M": 344,
    }
    assert results["key_metrics"].iloc[0]["metric_value"] == 10206.15


def test_quality_report_has_no_warn_or_fail(db) -> None:
    quality = run_data_quality_checks(db)
    assert set(quality["status"]) <= {"PASS", "INFO"}
    assert (quality["status"] == "PASS").sum() >= 9


def test_statistical_results_include_ci_and_cd4_signal(db) -> None:
    results = run_responder_analysis(db)
    stats = results["statistical_results"]
    timepoint = results["response_timepoint_summary"]
    changes = results["response_change_summary"]

    assert len(stats) == 5
    assert {"difference_ci_lower", "difference_ci_upper"} <= set(stats.columns)
    assert stats.loc[stats["population"] == "cd4_t_cell", "significant"].iloc[0]
    assert set(timepoint["time_from_treatment_start"]) == {0, 7, 14}
    assert set(changes["time_from_baseline"]) == {7, 14}
    assert {"ci_lower", "ci_upper"} <= set(timepoint.columns)
    assert {"ci_lower", "ci_upper"} <= set(changes.columns)

    for frame, mean_column, lower, upper in [
        (stats, "mean_difference", "difference_ci_lower", "difference_ci_upper"),
        (timepoint, "mean", "ci_lower", "ci_upper"),
        (changes, "mean_change", "ci_lower", "ci_upper"),
    ]:
        assert frame[[mean_column, lower, upper]].map(math.isfinite).all().all()
        assert (frame[lower] < frame[mean_column]).all()
        assert (frame[mean_column] < frame[upper]).all()


@pytest.mark.parametrize("replacement", [21, 7, 0])
def test_quality_report_rejects_incorrect_timepoints(db, replacement) -> None:
    expected_subjects = db.execute(
        """SELECT COUNT(DISTINCT s.subject_id)
           FROM subjects sub JOIN samples s ON s.subject_id = sub.subject_id
           WHERE sub.condition = 'melanoma' AND sub.treatment = 'miraclib'
             AND s.sample_type = 'PBMC' AND sub.response IN ('yes', 'no')"""
    ).fetchone()[0]
    db.execute(
        "UPDATE samples SET time_from_treatment_start = ? "
        "WHERE time_from_treatment_start = 14",
        (replacement,),
    )
    check = run_data_quality_checks(db).set_index("check_name").loc[
        "responder_subject_timepoints"
    ]
    assert check["status"] == "WARN"
    assert int(check["observed_value"]) == expected_subjects


def test_responder_calculations_match_known_values(db) -> None:
    # Retain cell counts for six eligible subjects. Nonresponders' B-cell
    # frequencies are nine percentage points below responders' frequencies.
    eligible = pd.read_sql_query(RESPONSE_ANALYSIS_SQL, db)
    subjects = {
        response: eligible.loc[eligible["response"] == response, "subject_id"]
        .drop_duplicates().iloc[:3].tolist()
        for response in ("yes", "no")
    }
    db.execute("DELETE FROM cell_counts")
    for response, ids in subjects.items():
        for index, subject in enumerate(ids):
            baseline = 10 * (index + 1) - (9 if response == "no" else 0)
            samples = db.execute(
                "SELECT sample_id, time_from_treatment_start FROM samples "
                "WHERE subject_id = ? AND sample_type = 'PBMC'", (subject,)
            ).fetchall()
            for sample, day in samples:
                # Total 1000: B cells and CD8 vary; other populations remain
                # positive and variable, avoiding degenerate Welch tests.
                value = baseline + (day // 7) * (index + 1)
                counts = [value * 10, value, value, value, 1000 - value * 13]
                db.executemany(
                    "INSERT INTO cell_counts VALUES (?, ?, ?)",
                    [(sample, population, count)
                     for population, count in zip(POPULATIONS, counts)],
                )

    results = run_responder_analysis(db)
    stats = results["statistical_results"].set_index("population").loc["b_cell"]
    # Subject means: responders [11, 22, 33], nonresponders [2, 13, 24].
    # Both sample variances are 121; Welch df = 4, t(.975, 4) below.
    difference_margin = 2.7764451051977987 * math.sqrt(242 / 3)
    assert stats["responder_n"] == stats["nonresponder_n"] == 3
    assert stats["responder_mean"] == pytest.approx(22)
    assert stats["nonresponder_mean"] == pytest.approx(13)
    assert stats["mean_difference"] == pytest.approx(9)
    assert stats["difference_ci_lower"] == pytest.approx(9 - difference_margin)
    assert stats["difference_ci_upper"] == pytest.approx(9 + difference_margin)

    timepoints = results["response_timepoint_summary"].set_index(
        ["response", "population", "time_from_treatment_start"]
    )
    changes = results["response_change_summary"].set_index(
        ["response", "population", "time_from_baseline"]
    )
    # At day 7, responder values are [11, 22, 33]; paired changes [1, 2, 3].
    # At day 14, paired changes are [2, 4, 6]. t(.975, 2) = 4.3026527297.
    t_critical = 4.302652729696142
    trend = timepoints.loc[("yes", "b_cell", 7)]
    assert trend["n"] == 3
    assert trend["mean"] == pytest.approx(22)
    assert trend["ci_lower"] == pytest.approx(22 - t_critical * 11 / math.sqrt(3))
    assert trend["ci_upper"] == pytest.approx(22 + t_critical * 11 / math.sqrt(3))
    for day, mean, std in [(7, 2, 1), (14, 4, 2)]:
        change = changes.loc[("yes", "b_cell", day)]
        assert change["n"] == 3
        assert change["mean_change"] == pytest.approx(mean)
        assert change["ci_lower"] == pytest.approx(mean - t_critical * std / math.sqrt(3))
        assert change["ci_upper"] == pytest.approx(mean + t_critical * std / math.sqrt(3))
