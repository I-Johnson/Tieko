---
name: streamlit-production-review
description: Build or review this project's Streamlit dashboard for correctness, usability, accessibility, performance, and production readiness. Use for dashboard code, filters, tables, charts, caching, responsive behavior, or deployment diagnostics.
---

# Streamlit production review

Read `dashboard.py`, `src/database.py`, `.streamlit/config.toml`, and dashboard
tests. Inspect the rendered application at narrow and wide viewports when browser
access is available.

## Preserve product behavior

- Keep the application in its configured light theme.
- Keep cohort definitions and statistical calculations outside presentation code.
- Make filters reflect the records returned by the query and handle empty results.
- Keep numerical displays formatted consistently with tabular numerals where alignment matters.
- Explain missing or outdated database tables with an actionable recovery path.

## Production checks

- Remember that Streamlit reruns the script after widget interactions.
- Cache serializable, read-only query results with `st.cache_data` only when freshness and invalidation are explicit.
- Use `st.cache_resource` only for thread-safe shared resources; do not share a mutable SQLite connection across sessions.
- Apply SQL filters before loading dataframes. Add pagination or aggregation before large tables reach the browser.
- Keep long-running computation out of the interactive request path.
- Verify keyboard access, focus visibility, labels, color contrast, readable chart text, touch targets, and responsive layout.
- Check browser and server logs for exceptions and deprecation warnings.

## Verification

Run Streamlit `AppTest` coverage for current, missing, and outdated database
states. Exercise each tab and its main interaction in a browser. Run `make test`
after code changes and report any behavior that could not be observed directly.
