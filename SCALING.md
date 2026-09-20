# Scaling the immune-cell trial analysis

## Current architecture

The repository uses one linear workflow:

```text
cell-count.csv
    -> load_data.py
    -> normalized SQLite tables and cell_frequencies view
    -> analysis.py
    -> derived analysis tables
    -> dashboard.py using Streamlit
```

This design fits a fixed take-home dataset, one deployment, and few writes. Keep
it until measurements show that data volume, concurrency, latency, or security
requirements have changed.

## Measure the source of growth

Answer these questions before choosing new infrastructure:

- How many rows, studies, populations, and files will the system store?
- How often will new data arrive, and how quickly must it become available?
- How many people and services will read or write at the same time?
- How long do analyses run, and how many cohort definitions must the system support?
- Will the system contain identifiable data or support regulatory work?
- What availability, recovery, and cost targets apply?

Change the component that causes the first measured problem. A larger dataset
alone does not require microservices.

## Stage 1: harden the current application

Continue using SQLite and Streamlit while they meet the workload.

- Record the source filename, checksum, ingestion time, schema version, and pipeline version.
- Preserve each raw input and write the derived database atomically.
- Make repeated loads produce the same result.
- Reject or quarantine invalid records with errors that identify the bad field.
- Add database migrations before deployments need to retain older databases.
- Cache read-only dashboard queries under a documented freshness policy.
- Apply SQL filters before loading data into a DataFrame.
- Run `make setup`, `make pipeline`, the tests, and a dashboard smoke test in continuous integration.
- Package the application in a container and keep development, staging, and production settings separate.
- Track pipeline duration, row counts, null rates, distribution changes, query latency, and application errors.

## Stage 2: handle recurring ingestion and concurrent users

Replace the database file when the application needs concurrent writes,
multiple instances, or direct network access. SQLite allows many readers but
only one writer at a time. Its documentation recommends a client and server
database for many concurrent network clients.

- Put application metadata and curated relational data in PostgreSQL.
- Put source files and large assay extracts in object storage.
- Use partitioned Parquet files when analytical queries benefit from columnar reads.
- Run ingestion and analysis as versioned background jobs.
- Give the dashboard a stable results API or a set of published result tables.
- Record job state and define retry, failure, and dead-letter behavior.
- Add connection pooling, indexes, pagination, and limits on returned rows.
- Add authentication, role-based access, secret storage, encryption, backups, and restore tests.

See [Appropriate Uses for SQLite](https://www.sqlite.org/whentouse.html).

## Stage 3: support multiple trials or regulated work

A production data model will need more than one CSV. It will probably include
studies, sites, subjects, treatment assignments, visits, specimens, assays,
population measurements, response assessments, and analysis dataset versions.
Treatment and response may need dated records instead of permanent columns on a
subject.

- Link each result to its source snapshot, transformation version, and analysis configuration.
- Define controlled terms, units, identifiers, and cohort rules.
- Keep raw, standardized, analysis-ready, and published results in separate layers.
- Restrict sensitive actions and record them in an audit log.
- Define retention and deletion rules with clinical, privacy, security, and legal teams.
- For regulatory submissions, assess CDISC SDTM for study data and ADaM for analysis datasets.

See [CDISC SDTM](https://www.cdisc.org/standards/foundational/sdtm/sdtm-v2-0)
and [CDISC ADaM](https://www.cdisc.org/standards/foundational/adam/primer).

## Improve the statistical analysis

The current pipeline averages days 0, 7, and 14 within each subject. It then
runs Welch's t-test for each population and applies the Benjamini-Hochberg
correction to the five p-values. This keeps subjects as the independent units,
which is appropriate for the assignment. Averaging also removes information
about how each population changes over time.

A prospective analysis should include the following work:

- Write the statistical analysis plan before inspecting outcomes.
- Evaluate a mixed-effects model with a subject-level random effect for longitudinal questions.
- Define covariates, contrasts, subgroup rules, and missing-data handling in advance.
- Define the multiplicity correction and sensitivity analyses in advance.
- Report effect sizes and confidence intervals with p-values.
- Record the cohort definition, source snapshot, software versions, random seeds, and result files.
- Ask a qualified statistician to review assumptions and diagnostics before clinical use.

The current analysis measures association. It does not predict the response of
a new patient. A prediction system needs a separate training and evaluation
pipeline. Keep every subject entirely in either training or validation. For
multi-site use, also test performance on a held-out site or external dataset.
Report discrimination, calibration, uncertainty, and subgroup performance.

See [scikit-learn grouped cross-validation](https://scikit-learn.org/1.0/modules/cross_validation.html)
and [FDA guidance on multiple endpoints](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/multiple-endpoints-clinical-trials).

## Decide whether Streamlit still fits

Streamlit can remain the internal analysis interface while separate services
handle ingestion and computation. Streamlit reruns the application after widget
interactions, so an uncached query may run many times.

- Keep cohort rules and statistical calculations outside `dashboard.py`.
- Cache serializable query results with `st.cache_data` and a defined expiration time.
- Use `st.cache_resource` only for thread-safe shared resources such as connection factories.
- Run search, sorting, filtering, aggregation, and pagination in the database for large tables.
- Send long analyses to background jobs and display their saved status or results.
- Add single sign-on and authorization before displaying patient-level data.
- Replace Streamlit only when the product needs a custom client, public API, or unsupported interaction pattern.

See the [Streamlit execution model](https://docs.streamlit.io/get-started/fundamentals/summary)
and [Streamlit caching guide](https://docs.streamlit.io/develop/concepts/architecture/caching).

## Explain the approach in an interview

One concise answer is:

> I chose SQLite and Streamlit because the assignment uses a fixed dataset and
> needs a reproducible local workflow. I would keep both until measurements show
> a problem with concurrency, volume, latency, or access control. Recurring data
> loads would first add immutable source storage, validation rules, job versions,
> and provenance. Concurrent writers or multiple application instances would
> move the relational data to PostgreSQL. Larger assay datasets could use
> partitioned Parquet files and an analytical engine. I would separate the
> dashboard from the analysis pipeline through published result tables or an
> API. For the statistics, I would replace the averaged comparison with a
> planned longitudinal model. A response predictor would use subject-grouped
> validation and predictive metrics instead of treating significance as proof
> of prediction.

For each proposed change, explain the measurement that triggers it, its cost,
its new failure modes, how you would test it, and how you would reverse it.
