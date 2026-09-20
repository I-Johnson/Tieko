# Immune-cell trial analysis

This project loads immune-cell counts from `cell-count.csv`, stores the data in SQLite, compares cell-population frequencies between responders and non-responders, and presents the results in a Streamlit dashboard.

The questions, methods, results, cohort definitions, and limitations are documented in the [analysis report](report.md).

## Run the project

```bash
make setup
make pipeline
make dashboard
```

The dashboard runs at `[https://johnsontieko.streamlit.app]([url](https://johnsontieko.streamlit.app/))`. In GitHub Codespaces, open the forwarded port link.

## Main files

- `load_data.py` validates the CSV and builds the normalized SQLite database.
- `analysis.py` runs the frequency, responder, baseline, and data-quality analyses.
- `dashboard.py` serves the interactive results.
- `SCALING.md` describes how the system could evolve for larger datasets and more users.
- `report.md` contains the full analysis and current answers.
