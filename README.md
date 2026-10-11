# Immune Cell Response Explorer

A reproducible clinical immune-cell analysis pipeline and interactive dashboard. The project loads 10,500 samples into a normalized SQLite database, calculates per-sample population frequencies, compares miraclib responders with non-responders, and reports the requested baseline subsets.

## Reviewer quick start

Open the repository in GitHub Codespaces, then run:

```bash
make setup
make pipeline
make dashboard
```

Open forwarded port **8050** from the Codespaces **Ports** tab. No arguments, credentials, or external database are required.

| Resource | Link |
|---|---|
| Interactive dashboard | Port **8050** after running `make dashboard` |
| Health check | `http://localhost:8050/healthz` |
| Continuous integration | GitHub Actions → CI |

Useful verification commands:

```bash
make test              # unit + integration tests with coverage
make test-unit         # fast isolated calculations and validation
make test-integration  # real-data pipeline, queries, and HTTP smoke test
make check             # lint, types, pipeline, tests, dependency audit
```

The three required grading targets are implemented exactly as `make setup`, `make pipeline`, and `make dashboard`. `python load_data.py` also runs directly without arguments and creates `cell_counts.db` in the repository root.

## Results

The primary analysis uses all eligible longitudinal PBMC samples while treating the subject—not each repeated sample—as the independent unit. CD4 T-cell frequency is the only FDR-significant difference:

| Measure | Responders | Non-responders | Difference | Raw p | FDR p | Cohen's d |
|---|---:|---:|---:|---:|---:|---:|
| CD4 T-cell frequency | 30.54% | 29.90% | +0.64 pp | 0.00451 | 0.0226 | 0.22 |

The effect is small. A baseline-only sensitivity analysis finds no significant population after FDR correction. The all-timepoint result should therefore be treated as an exploratory treatment-response association, not a validated pretreatment predictor. Demonstrating predictive performance would require a defined prediction time, train/test separation, and an independent validation cohort.

### Requested baseline subset

The melanoma, miraclib, PBMC, day-0 subset contains **656 samples and subjects**:

| Breakdown | Count |
|---|---:|
| `prj1` | 384 |
| `prj3` | 272 |
| Responders | 331 |
| Non-responders | 325 |
| Male | 344 |
| Female | 312 |

For male melanoma responders at day 0 across all sample and treatment types, the mean B-cell count is **10,206.15**.

The assignment also requests mention of **quintazide**. It is not present in the supplied data and is not introduced into any cohort or calculation.

## Statistical design

The response comparison includes melanoma subjects receiving miraclib with PBMC samples and a recorded `yes` or `no` response. Relative frequency is calculated as:

```text
100 × population count / total count across the five populations
```

Each subject's repeated timepoints are averaged before a two-sided Welch independent-samples t-test. This prevents longitudinal observations from being counted as independent replicates. The analysis reports group sizes and means, mean difference, Cohen's d, raw p-value, and Benjamini-Hochberg-adjusted p-value across the five populations. Adjusted p-values below 0.05 are marked significant.

The dashboard boxplots show sample-level distributions, while both the primary and baseline-only inferential tables use independent subjects.

## Architecture

The required root scripts are thin entry points. Application logic is separated by responsibility inside `teiko/`:

```text
cell-count.csv
      │
      ▼
CellCountLoader ──► normalized SQLite ──► ResponseAnalyzer
                         │                       │
                         └────► AnalysisRepository
                                           │
                                           ▼
                                    DashboardFactory
```

- `Settings`: immutable configuration with environment overrides.
- `Database`: connection, foreign-key, schema, and integrity lifecycle.
- `CellCountLoader`: validation, normalization, transactions, and atomic replacement.
- `ResponseStatistics`: storage-independent statistical calculations.
- `ResponseAnalyzer`: cohort extraction and atomic result persistence.
- `AnalysisRepository`: parameterized read-only queries and server-side pagination.
- `DashboardFactory`: injectable Dash/Flask application construction.

Supported environment variables are `CELL_COUNT_CSV`, `CELL_COUNT_DB`, `ANALYSIS_ALPHA`, and `PORT`.

## Relational model

- `subjects`: one row per participant and stable clinical metadata.
- `samples`: one row per biological sample, linked to its subject.
- `cell_counts`: one row per sample and immune population.
- `sample_frequencies`: SQL view with `sample`, `total_count`, `population`, `count`, and `percentage`.
- `analysis_results`: named primary and sensitivity-analysis outputs.

Primary and foreign keys, domain checks, indexes, row validation, transactions, atomic replacement, and SQLite integrity checks protect data quality. The long-form population table allows new cell populations without adding repeated count columns.

## Testing and quality controls

The test suite covers:

- known-value FDR correction and effect-size calculations;
- within-subject aggregation of longitudinal observations;
- malformed metadata, invalid counts, duplicate samples, and failed-reload recovery;
- complete real-data cardinality, integrity, frequencies, and requested answers;
- server-side paging, filtering, allowlisted sorting, and injection resistance;
- dashboard rendering and the production health endpoint.

CI runs on Python **3.11–3.14**. Ruff enforces formatting and lint rules, mypy checks application types, pytest enforces at least 80% coverage, and `pip-audit` checks pinned runtime dependencies. A separate CI job builds the final container, starts it, and requires `/healthz` to respond.

Runtime packages are pinned in `requirements.txt`; development and quality tooling is pinned separately in `requirements-dev.txt`.

## Optional container execution

Build and run the production image locally:

```bash
docker compose up --build
```

The multi-stage image:

- builds the database and analyses during image construction;
- excludes the source CSV, tests, and development tools from the runtime stage;
- runs as an unprivileged user;
- serves through Gunicorn;
- includes a Docker health check.

The container is optional; evaluators can use the required Make targets directly in Codespaces. When `make dashboard` starts the server, Codespaces detects port 8050 and provides the dashboard link from its **Ports** tab. The Docker image remains available as evidence that the same application can run consistently outside Codespaces; another container host can use it by setting `PORT`.
