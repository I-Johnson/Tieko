"""Interactive Streamlit dashboard for the cell-count analysis."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import DATABASE_PATH, POPULATIONS
from src.database import read_query

st.set_page_config(
    page_title="Immune Cell Trial Analysis",
    page_icon="🧬",
    layout="wide",
)


def apply_visual_style() -> None:
    """Apply typography and surface polish without changing app behavior."""
    st.markdown(
        """
        <style>
        :root {
            color-scheme: light;
            --surface-card: rgba(255, 255, 255, 0.82);
            --surface-subtle: rgba(15, 23, 42, 0.025);
            --shadow-border:
                0 0 0 1px oklch(0 0 0 / 0.06),
                0 1px 2px -1px oklch(0 0 0 / 0.06),
                0 2px 4px 0 oklch(0 0 0 / 0.04);
            --shadow-border-hover:
                0 0 0 1px oklch(0 0 0 / 0.08),
                0 1px 2px -1px oklch(0 0 0 / 0.08),
                0 2px 4px 0 oklch(0 0 0 / 0.06);
        }

        html {
            color-scheme: light;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            font-family: system-ui, -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif;
        }

        h1, h2, h3,
        [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"] {
            text-wrap: balance;
        }

        p, li, label, figcaption, blockquote,
        [data-testid="stCaptionContainer"],
        [data-testid="stAlertContent"] {
            text-wrap: pretty;
        }

        [data-testid="stMetricValue"],
        [data-testid="stDataFrame"],
        [data-testid="stTable"] {
            font-variant-numeric: tabular-nums;
        }

        [data-testid="stMainBlockContainer"] {
            max-width: 76rem;
            padding-top: 4.5rem;
            padding-bottom: 5rem;
        }

        [data-testid="stMainBlockContainer"] > div:first-child {
            gap: 1.15rem;
        }

        h1 {
            letter-spacing: -0.04em;
            line-height: 1.05;
        }

        h2, h3 {
            letter-spacing: -0.025em;
            line-height: 1.15;
        }

        [data-testid="stCaptionContainer"] {
            font-size: 0.95rem;
        }

        [data-testid="stMetric"] {
            min-height: 7.75rem;
            padding: 1.15rem 1.25rem;
            border-radius: 16px;
            background: var(--surface-card);
            box-shadow: var(--shadow-border);
            transition: box-shadow 150ms ease-out, transform 150ms ease-out;
        }

        [data-testid="stMetric"]:hover {
            box-shadow: var(--shadow-border-hover);
            transform: translateY(-1px);
        }

        [data-testid="stMetricLabel"] {
            margin-bottom: 0.3rem;
        }

        [data-testid="stMetricValue"] {
            letter-spacing: -0.035em;
        }

        [data-testid="stDataFrame"],
        [data-testid="stTable"],
        [data-testid="stPlotlyChart"] {
            overflow: hidden;
            border-radius: 16px;
            background: var(--surface-card);
            box-shadow: var(--shadow-border);
        }

        [data-testid="stPlotlyChart"] {
            padding: 8px;
        }

        [data-testid="stDownloadButton"] > button {
            min-height: 44px;
            padding-left: 16px;
            padding-right: 14px;
            border: 0;
            border-radius: 12px;
            box-shadow: var(--shadow-border);
            transition: box-shadow 150ms ease-out, transform 150ms ease-out;
        }

        [data-testid="stDownloadButton"] > button:hover {
            box-shadow: var(--shadow-border-hover);
            transform: translateY(-1px);
        }

        [data-testid="stTabs"] [role="tab"] {
            min-height: 44px;
            padding-left: 16px;
            padding-right: 16px;
        }

        [data-baseweb="select"] > div,
        [data-baseweb="input"] > div,
        [data-baseweb="tag"] {
            border-radius: 12px;
        }

        [data-baseweb="select"] > div,
        [data-baseweb="input"] > div {
            min-height: 44px;
        }

        [data-testid="stExpander"] {
            overflow: hidden;
            border: 0;
            border-radius: 16px;
            background: var(--surface-subtle);
            box-shadow: var(--shadow-border);
        }

        [data-testid="stAlert"] {
            border-radius: 14px;
        }

        img {
            border-radius: 12px;
            outline: 1px solid oklch(0 0 0 / 0.1);
            outline-offset: -1px;
        }

        @media (max-width: 640px) {
            [data-testid="stMainBlockContainer"] {
                padding-top: 3.75rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }

            [data-testid="stMetric"] {
                min-height: 6.5rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def require_database() -> bool:
    if not DATABASE_PATH.is_file():
        st.error(
            "The SQLite database has not been created yet. Run "
            "`python load_data.py` followed by `python analysis.py`, or run "
            "`make pipeline`."
        )
        return False

    required_tables = {
        "projects", "subjects", "samples", "cell_counts", "cell_frequencies",
        "statistical_results", "response_subject_frequencies",
        "response_timepoint_summary", "response_change_summary",
        "baseline_samples", "baseline_project_counts", "baseline_response_counts",
        "baseline_sex_counts", "key_metrics", "data_quality_checks",
    }
    available_tables = read_query(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
    )
    missing_tables = required_tables - set(available_tables["name"])
    if missing_tables:
        st.error(
            "The database is incomplete or was generated by an older version. "
            "Run `make pipeline` to rebuild it before opening the dashboard. "
            "Missing tables or views: " + ", ".join(sorted(missing_tables)) + "."
        )
        return False
    return True


def download_csv(frame: pd.DataFrame, filename: str, label: str) -> None:
    """Render a consistent CSV download control for a result table."""
    st.download_button(
        label=label,
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )


def show_overview() -> None:
    st.header("Data overview")
    st.write(
        "This table shows each immune-cell population as a percentage of the "
        "total cells in its sample."
    )

    overview_counts = read_query(
        """
        SELECT
            (SELECT COUNT(*) FROM projects) AS projects,
            (SELECT COUNT(*) FROM subjects) AS subjects,
            (SELECT COUNT(*) FROM samples) AS samples,
            (SELECT COUNT(*) FROM cell_counts) AS cell_count_records
        """
    ).iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Projects", f"{int(overview_counts['projects']):,}")
    c2.metric("Subjects", f"{int(overview_counts['subjects']):,}")
    c3.metric("Samples", f"{int(overview_counts['samples']):,}")
    c4.metric("Cell-count records", f"{int(overview_counts['cell_count_records']):,}")

    metadata_options = read_query(
        """
        SELECT DISTINCT condition, treatment, sample_type,
                        time_from_treatment_start
        FROM samples s JOIN subjects sub ON sub.subject_id = s.subject_id
        ORDER BY condition, treatment, sample_type, time_from_treatment_start
        """
    )
    filter_cols = st.columns(4)
    conditions = ["All"] + sorted(metadata_options["condition"].unique().tolist())
    treatments = ["All"] + sorted(metadata_options["treatment"].unique().tolist())
    sample_types = ["All"] + sorted(metadata_options["sample_type"].unique().tolist())
    timepoints = ["All"] + sorted(metadata_options["time_from_treatment_start"].unique().tolist())
    selected_condition = filter_cols[0].selectbox("Condition", conditions)
    selected_treatment = filter_cols[1].selectbox("Treatment", treatments)
    selected_sample_type = filter_cols[2].selectbox("Sample type", sample_types)
    selected_timepoint = filter_cols[3].selectbox("Time from treatment start", timepoints)

    sample_ids = read_query(
        """
        SELECT DISTINCT f.sample
        FROM cell_frequencies f
        JOIN samples s ON s.sample_id = f.sample
        JOIN subjects sub ON sub.subject_id = s.subject_id
        WHERE (? = 'All' OR sub.condition = ?)
          AND (? = 'All' OR sub.treatment = ?)
          AND (? = 'All' OR s.sample_type = ?)
          AND (? = 'All' OR CAST(s.time_from_treatment_start AS TEXT) = ?)
        ORDER BY f.sample
        """,
        (
            selected_condition,
            selected_condition,
            selected_treatment,
            selected_treatment,
            selected_sample_type,
            selected_sample_type,
            str(selected_timepoint),
            str(selected_timepoint),
        ),
    )
    selected_sample = st.selectbox(
        "Inspect one sample",
        options=["All samples"] + sample_ids["sample"].tolist(),
    )
    if selected_sample == "All samples":
        frequency_query = """
            SELECT f.*
            FROM cell_frequencies f
            JOIN samples s ON s.sample_id = f.sample
            JOIN subjects sub ON sub.subject_id = s.subject_id
            WHERE (? = 'All' OR sub.condition = ?)
              AND (? = 'All' OR sub.treatment = ?)
              AND (? = 'All' OR s.sample_type = ?)
              AND (? = 'All' OR CAST(s.time_from_treatment_start AS TEXT) = ?)
            ORDER BY f.sample, f.population
        """
        frequency_params = (
            selected_condition,
            selected_condition,
            selected_treatment,
            selected_treatment,
            selected_sample_type,
            selected_sample_type,
            str(selected_timepoint),
            str(selected_timepoint),
        )
    else:
        frequency_query = "SELECT * FROM cell_frequencies WHERE sample = ? ORDER BY population"
        frequency_params = (selected_sample,)
    frequencies = read_query(frequency_query, frequency_params)

    selected_populations = st.multiselect(
        "Populations to display",
        options=POPULATIONS,
        default=POPULATIONS,
    )
    if selected_populations:
        frequencies = frequencies[frequencies["population"].isin(selected_populations)]
    else:
        st.info("Select at least one population to display the table.")

    # Pandas Styler has a default 262,144-cell render limit. The all-samples
    # view has 52,500 rows, so pass it directly to Streamlit; styling is safe
    # and useful for the much smaller single-sample view.
    if selected_sample == "All samples":
        st.dataframe(
            frequencies,
            use_container_width=True,
            hide_index=True,
            height=520,
        )
    else:
        st.dataframe(
            frequencies.style.format(
                {
                    "total_count": "{:,.0f}",
                    "count": "{:,.0f}",
                    "percentage": "{:.2f}%",
                }
            ),
            use_container_width=True,
            hide_index=True,
            height=520,
        )
    download_csv(frequencies, "cell_frequencies.csv", "Download frequency CSV")


def show_responder_analysis() -> None:
    st.header("Miraclib responder analysis")
    st.write(
        "This analysis includes melanoma PBMC samples from patients treated "
        "with miraclib. Percentages were averaged across days 0, 7, and 14 "
        "within each subject before comparing response groups."
    )

    stats = read_query(
        "SELECT * FROM statistical_results ORDER BY population"
    )
    subject_frequencies = read_query(
        """
        SELECT subject_id, response, population, subject_mean_percentage
        FROM response_subject_frequencies
        ORDER BY population, response, subject_id
        """
    )
    timepoint_summary = read_query(
        "SELECT * FROM response_timepoint_summary ORDER BY population, time_from_treatment_start, response"
    )
    change_summary = read_query(
        "SELECT * FROM response_change_summary ORDER BY population, time_from_baseline, response"
    )

    responders = int(stats["responder_n"].iloc[0])
    nonresponders = int(stats["nonresponder_n"].iloc[0])
    c1, c2, c3 = st.columns(3)
    c1.metric("Responders", f"{responders:,}")
    c2.metric("Non-responders", f"{nonresponders:,}")
    significant = stats.loc[stats["significant"].astype(bool), "population"].tolist()
    c3.metric("Significant populations", ", ".join(significant) or "None")

    plot_data = subject_frequencies.copy()
    plot_data["response"] = plot_data["response"].map(
        {"yes": "Responder", "no": "Non-responder"}
    )
    figure = px.box(
        plot_data,
        x="response",
        y="subject_mean_percentage",
        facet_col="population",
        facet_col_wrap=3,
        color="response",
        category_orders={
            "response": ["Responder", "Non-responder"],
            "population": POPULATIONS,
        },
        labels={
            "response": "Response group",
            "subject_mean_percentage": "Mean population frequency (%)",
            "population": "Population",
        },
        title="Subject-level immune-cell frequencies by response group",
        points=False,
    )
    figure.update_layout(showlegend=False, height=600)
    st.plotly_chart(figure, use_container_width=True)

    st.subheader("Change over time")
    view = st.radio(
        "Responder view",
        ["Population frequency by time point", "Change from baseline"],
        horizontal=True,
    )
    if view == "Population frequency by time point":
        selected_population = st.selectbox(
            "Population for time trend", POPULATIONS, key="trend_population"
        )
        trend = timepoint_summary[
            timepoint_summary["population"] == selected_population
        ].copy()
        trend["response_label"] = trend["response"].map(
            {"yes": "Responder", "no": "Non-responder"}
        )
        trend_figure = px.line(
            trend,
            x="time_from_treatment_start",
            y="mean",
            color="response_label",
            error_y=trend["ci_upper"] - trend["mean"],
            error_y_minus=trend["mean"] - trend["ci_lower"],
            markers=True,
            labels={
                "time_from_treatment_start": "Days from treatment start",
                "mean": "Mean frequency (%)",
                "response_label": "Response group",
            },
            title=f"{selected_population} frequency over time with 95% CI",
        )
        st.plotly_chart(trend_figure, use_container_width=True)
        download_csv(trend, "responder_timepoint_summary.csv", "Download time-point CSV")
    else:
        selected_population = st.selectbox(
            "Population for baseline-change trend", POPULATIONS, key="change_population"
        )
        changes = change_summary[change_summary["population"] == selected_population].copy()
        changes["response_label"] = changes["response"].map(
            {"yes": "Responder", "no": "Non-responder"}
        )
        change_figure = px.line(
            changes,
            x="time_from_baseline",
            y="mean_change",
            color="response_label",
            error_y=changes["ci_upper"] - changes["mean_change"],
            error_y_minus=changes["mean_change"] - changes["ci_lower"],
            markers=True,
            labels={
                "time_from_baseline": "Days from baseline",
                "mean_change": "Change from baseline (percentage points)",
                "response_label": "Response group",
            },
            title=f"{selected_population} change from baseline with 95% CI",
        )
        st.plotly_chart(change_figure, use_container_width=True)
        download_csv(changes, "responder_change_summary.csv", "Download baseline-change CSV")

    display_stats = stats.copy()
    display_stats["significant"] = display_stats["significant"].astype(bool).map(
        {True: "Yes", False: "No"}
    )
    numeric_columns = [
        "responder_mean",
        "nonresponder_mean",
        "responder_median",
        "nonresponder_median",
        "mean_difference",
        "p_value",
        "adjusted_p_value",
    ]
    st.subheader("Statistical results")
    st.dataframe(
        display_stats.style.format({column: "{:.4f}" for column in numeric_columns}),
        use_container_width=True,
        hide_index=True,
    )
    download_csv(display_stats, "statistical_results.csv", "Download statistical results CSV")

    if significant:
        st.success(
            "The statistically significant population after Benjamini–Hochberg "
            f"correction is: {', '.join(significant)}. This is an association "
            "in this dataset, not proof of clinical predictive performance."
        )
    else:
        st.info("No population passed the adjusted p-value threshold of 0.05.")


def show_baseline_subset() -> None:
    st.header("Baseline melanoma PBMC subset")
    st.write(
        "This section includes melanoma PBMC samples at day 0 from patients "
        "treated with miraclib. Counts are based on unique subjects where the "
        "question asks for subjects."
    )

    baseline_count = int(
        read_query("SELECT COUNT(*) AS n FROM baseline_samples").iloc[0]["n"]
    )
    metric = read_query("SELECT * FROM key_metrics").iloc[0]
    c1, c2 = st.columns(2)
    c1.metric("Baseline samples", f"{baseline_count:,}")
    c2.metric("Average B cells, requested subgroup", f"{metric['metric_value']:.2f}")

    download_csv(read_query("SELECT * FROM baseline_samples ORDER BY sample_id"), "baseline_samples.csv", "Download baseline samples CSV")

    left, right = st.columns(2)
    with left:
        st.subheader("Samples by project")
        project_counts = read_query(
            "SELECT * FROM baseline_project_counts ORDER BY project_id"
        )
        st.dataframe(project_counts, use_container_width=True, hide_index=True)
        st.bar_chart(project_counts.set_index("project_id"))

    with right:
        st.subheader("Subjects by response")
        response_counts = read_query(
            "SELECT * FROM baseline_response_counts ORDER BY response"
        )
        st.dataframe(response_counts, use_container_width=True, hide_index=True)
        st.bar_chart(response_counts.set_index("response"))

    st.subheader("Subjects by sex")
    sex_counts = read_query("SELECT * FROM baseline_sex_counts ORDER BY sex")
    st.dataframe(sex_counts, use_container_width=True, hide_index=True)
    st.bar_chart(sex_counts.set_index("sex"))

    with st.expander("Show baseline sample records"):
        st.dataframe(
            read_query("SELECT * FROM baseline_samples ORDER BY sample_id"),
            use_container_width=True,
            hide_index=True,
            height=420,
        )


def main() -> None:
    apply_visual_style()
    st.title("Immune Cell Trial Analysis")
    st.caption("Loblaw Bio clinical-trial cell-count dashboard")
    st.sidebar.header("About this dashboard")
    st.sidebar.write(
        "The source CSV uses `condition`, `sex`, and `sample`; these correspond "
        "to indication, gender, and sample ID in the assignment."
    )
    st.sidebar.info(
        "Quintazide is not a treatment or field in the supplied dataset, so it "
        "is not included in any calculation."
    )

    if not require_database():
        return

    quality = read_query(
        "SELECT * FROM data_quality_checks ORDER BY status, check_name"
    )
    with st.sidebar.expander("Data quality checks", expanded=False):
        status_counts = quality["status"].value_counts().to_dict()
        st.write(
            f"Pass: {status_counts.get('PASS', 0)} | "
            f"Info: {status_counts.get('INFO', 0)} | "
            f"Warn/fail: {status_counts.get('WARN', 0) + status_counts.get('FAIL', 0)}"
        )
        st.dataframe(quality, use_container_width=True, hide_index=True)
        download_csv(quality, "data_quality_checks.csv", "Download quality report")

    overview_tab, responder_tab, baseline_tab = st.tabs(
        ["Data overview", "Responder analysis", "Baseline subset"]
    )
    with overview_tab:
        show_overview()
    with responder_tab:
        show_responder_analysis()
    with baseline_tab:
        show_baseline_subset()


if __name__ == "__main__":
    main()
