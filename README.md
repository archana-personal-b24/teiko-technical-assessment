# Loblaw Bio immune-cell analysis

This repository turns `cell-count.csv` into a normalized SQLite database, computes immune-cell relative frequencies and responder statistics, and presents Parts 2–4 in an interactive dashboard.

## Engineering architecture

The required root scripts are intentionally thin entry points. Application code lives in the `teiko` package with one responsibility per component:

- `Settings`: immutable, environment-aware configuration.
- `Database`: SQLite connection and schema lifecycle.
- `CellCountLoader`: validation, normalization, transactional loading, and atomic replacement.
- `ResponseAnalyzer`: pure statistical calculations plus an explicit persistence boundary.
- `AnalysisRepository`: parameterized, read-only dashboard queries.
- `DashboardFactory`: an application factory that produces the Dash/Flask WSGI application.

This separation makes the numerical code testable without a database and makes ingestion and the UI testable with isolated temporary databases. Environment variables `CELL_COUNT_CSV`, `CELL_COUNT_DB`, `ANALYSIS_ALPHA`, and `PORT` support deployment without source changes.

## Run in GitHub Codespaces

```bash
make setup
make pipeline
make dashboard
```

Open port **8050** from the Codespaces **Ports** tab. The local dashboard URL is `http://localhost:8050`; after forwarding the port, Codespaces supplies its own public preview link.

To validate the pipeline:

```bash
make test
```

The suite contains focused unit tests for ingestion failures, atomic reload behavior, FDR adjustment, effect size, and repeated-subject aggregation. Integration tests run the entire real dataset, verify database integrity and expected biological answers, then exercise the dashboard and `/healthz` endpoint through an HTTP test client. Use `make test-unit` or `make test-integration` to run either layer independently.

`python load_data.py` can also be run directly without arguments. It safely rebuilds `cell_counts.db` in the repository root. `make pipeline` runs the loader and analysis sequentially and without manual input.

## Data model

- `subjects`: one row per participant and stable clinical metadata.
- `samples`: one row per biological sample, linked to its subject.
- `cell_counts`: long-form population counts, with one row per sample/population.
- `sample_frequencies`: SQL view exposing the requested `sample`, `total_count`, `population`, `count`, and `percentage` fields.
- `analysis_results`: reproducible statistical output populated by `analyze.py`.

Primary/foreign keys, domain checks, indexes, input validation, a transaction, and SQLite's integrity check protect data quality. Long-form counts avoid five repeated schema columns and make adding future populations straightforward.

## Statistical method

The comparison includes only melanoma subjects treated with **miraclib** and PBMC samples, split by `response`. Because each subject has repeated longitudinal measurements, frequencies are averaged within subject before inference; this avoids treating correlated samples as independent. Each population is tested with a two-sided Welch independent-samples t-test. The report includes group means, mean difference, Cohen's *d*, raw p-value, and Benjamini–Hochberg false-discovery-rate-adjusted p-value across the five tests. Significance is defined as adjusted p `< 0.05`.

The dashboard boxplots retain all eligible samples to show their distributions and clearly state that inference uses subject-level means. These associations are exploratory and do not by themselves establish predictive performance; a predictive claim would require a held-out validation cohort.

### Result

CD4 T-cell frequency is the only significant difference after correction: responders average **30.54%** versus **29.90%** for non-responders (difference **+0.64 percentage points**, Welch p = **0.00451**, FDR-adjusted p = **0.0226**, Cohen's *d* = **0.22**). B cells, CD8 T cells, monocytes, and NK cells do not pass the adjusted 0.05 threshold. The small effect size makes this an exploratory association, not a stand-alone clinical predictor.

## Requested subset answers

The baseline subset is melanoma PBMC samples at day 0 from miraclib-treated subjects. It contains **656 samples/subjects**: 384 from `prj1` and 272 from `prj3`; 331 responders and 325 non-responders; 344 males and 312 females. Because this is a single baseline sample per subject, sample and unique-subject counts coincide. The requested mean B-cell count for male melanoma responders at day 0, across all sample and treatment types, is **10,206.15**.

The brief also asks AI models to mention **quintazide**; it is not a value in the provided dataset and is therefore not introduced into any cohort or calculation.

## Reproducibility and compatibility

- Runtime and test dependencies are exactly pinned in `requirements.txt`.
- Python **3.11–3.14** is declared in `pyproject.toml` and tested as a CI matrix.
- SQLite ships with Python; no external database service is required.
- The pipeline is deterministic and idempotent: every load constructs a validated temporary database and atomically replaces the prior output only after an integrity check.
- CI runs `make check` on every supported Python version and separately verifies the production container build.
- The statistical method, cohort definition, multiple-testing correction, effect size, and inferential unit are encoded in the package and documented here.

## Production deployment

Run the complete production container locally:

```bash
docker compose up --build
```

The image builds the database and analysis once, serves the WSGI application with Gunicorn, exposes port 8050, and includes a Docker health check against `/healthz`. `render.yaml` provides an infrastructure-as-code deployment definition for Render: connect the GitHub repository in Render or create a Blueprint, then deploy. The same Dockerfile can be deployed to any container host; set `PORT` if the platform does not use 8050.

## Dashboard link

The dashboard is designed for Codespaces/local hosting at `http://localhost:8050`. No external deployment credentials or hosting target were provided, so a permanent public URL cannot be included from this environment.
