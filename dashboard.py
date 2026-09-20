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


def require_database() -> bool:
    if DATABASE_PATH.is_file():
        return True

    st.error(
        "The SQLite database has not been created yet. Run "
        "`python load_data.py` followed by `python analysis.py`, or run "
        "`make pipeline`."
    )
    return False


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

    sample_ids = read_query("SELECT sample FROM cell_frequencies ORDER BY sample")
    selected_sample = st.selectbox(
        "Inspect one sample",
        options=["All samples"] + sample_ids["sample"].tolist(),
    )
    if selected_sample == "All samples":
        frequency_query = "SELECT * FROM cell_frequencies ORDER BY sample, population"
    else:
        frequency_query = (
            "SELECT * FROM cell_frequencies "
            "WHERE sample = ? ORDER BY population"
        )
    frequencies = read_query(
        frequency_query,
        (selected_sample,) if selected_sample != "All samples" else (),
    )

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

    responders = int(stats["responder_n"].iloc[0])
    nonresponders = int(stats["nonresponder_n"].iloc[0])
    c1, c2, c3 = st.columns(3)
    c1.metric("Responders", f"{responders:,}")
    c2.metric("Non-responders", f"{nonresponders:,}")
    significant = stats.loc[stats["significant"], "population"].tolist()
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

    display_stats = stats.copy()
    display_stats["significant"] = display_stats["significant"].map(
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
