"""Statistical analysis for treatment-response cohorts."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd
from scipy import stats

from teiko.database import Database

RESULT_COLUMNS = [
    "analysis_name", "population", "n_responders", "n_nonresponders",
    "mean_responder", "mean_nonresponder", "mean_difference", "t_statistic",
    "p_value", "adjusted_p_value", "cohens_d", "significant",
]


@dataclass(frozen=True)
class CohortDefinition:
    """Database filters defining an analysis cohort."""

    name: str = "all_timepoints"
    condition: str = "melanoma"
    treatment: str = "miraclib"
    sample_type: str = "PBMC"
    timepoint: int | None = None


class ResponseStatistics:
    """Pure statistical calculations, independent of storage."""

    def __init__(self, alpha: float = 0.05):
        if not 0 < alpha < 1:
            raise ValueError("alpha must be between 0 and 1")
        self.alpha = alpha

    @staticmethod
    def adjust_pvalues(p_values: list[float]) -> np.ndarray:
        """Apply Benjamini-Hochberg false-discovery-rate adjustment."""
        values = np.asarray(p_values, dtype=float)
        invalid = (
            values.ndim != 1
            or len(values) == 0
            or np.any((values < 0) | (values > 1) | np.isnan(values))
        )
        if invalid:
            raise ValueError("p-values must be a non-empty 1D sequence in [0, 1]")
        order = np.argsort(values)
        ranked = values[order]
        adjusted_ranked = np.minimum.accumulate(
            (ranked * len(values) / np.arange(1, len(values) + 1))[::-1]
        )[::-1]
        adjusted = np.empty_like(adjusted_ranked)
        adjusted[order] = np.clip(adjusted_ranked, 0, 1)
        return adjusted

    @staticmethod
    def cohens_d(first: np.ndarray, second: np.ndarray) -> float:
        """Calculate pooled-standard-deviation Cohen's d."""
        if len(first) < 2 or len(second) < 2:
            raise ValueError("Cohen's d requires at least two observations per group")
        pooled_sd = np.sqrt(
            ((len(first) - 1) * first.var(ddof=1)
             + (len(second) - 1) * second.var(ddof=1))
            / (len(first) + len(second) - 2)
        )
        return float((first.mean() - second.mean()) / pooled_sd) if pooled_sd else 0.0

    def calculate(self, observations: pd.DataFrame, analysis_name: str) -> pd.DataFrame:
        """Compare response groups after averaging repeated samples per subject."""
        required = {"subject_id", "response", "population", "percentage"}
        if observations.empty:
            raise ValueError("Analysis cohort is empty")
        if not required.issubset(observations.columns):
            raise ValueError(f"Observations require columns: {sorted(required)}")
        subject_means = observations.groupby(
            ["subject_id", "response", "population"], as_index=False
        )["percentage"].mean()

        rows: list[list[object]] = []
        p_values: list[float] = []
        for population, frame in subject_means.groupby("population", sort=True):
            responders = frame.loc[frame.response == "yes", "percentage"].to_numpy(float)
            nonresponders = frame.loc[frame.response == "no", "percentage"].to_numpy(float)
            if len(responders) < 2 or len(nonresponders) < 2:
                raise ValueError(f"Population {population} has fewer than two subjects per group")
            test = stats.ttest_ind(responders, nonresponders, equal_var=False)
            p_values.append(float(test.pvalue))
            rows.append([
                analysis_name, population, len(responders), len(nonresponders),
                responders.mean(), nonresponders.mean(),
                responders.mean() - nonresponders.mean(), test.statistic,
                test.pvalue, 0.0, self.cohens_d(responders, nonresponders), 0,
            ])
        for row, adjusted in zip(rows, self.adjust_pvalues(p_values), strict=True):
            row[9] = float(adjusted)
            row[11] = int(adjusted < self.alpha)
        return pd.DataFrame(rows, columns=RESULT_COLUMNS)


class ResponseAnalyzer:
    """Orchestrate cohort extraction, calculation, and persistence."""

    def __init__(self, database: Database, alpha: float = 0.05,
                 cohort: CohortDefinition = CohortDefinition()):
        self.database = database
        self.cohort = cohort
        self.statistics = ResponseStatistics(alpha)

    def observations(self, cohort: CohortDefinition) -> pd.DataFrame:
        query = """
            SELECT s.subject_id, s.response, f.population, f.percentage
            FROM sample_frequencies AS f
            JOIN samples AS x ON x.sample_id = f.sample
            JOIN subjects AS s ON s.subject_id = x.subject_id
            WHERE s.condition = ? AND s.treatment = ? AND x.sample_type = ?
              AND s.response IN ('yes', 'no')
        """
        parameters: list[object] = [cohort.condition, cohort.treatment, cohort.sample_type]
        if cohort.timepoint is not None:
            query += " AND x.time_from_treatment_start = ?"
            parameters.append(cohort.timepoint)
        with self.database.connect() as connection:
            return pd.read_sql_query(query, connection, params=parameters)

    def analyze_cohort(self, cohort: CohortDefinition) -> pd.DataFrame:
        return self.statistics.calculate(self.observations(cohort), cohort.name)

    def run_and_persist(self) -> pd.DataFrame:
        """Persist primary and baseline sensitivity analyses atomically."""
        baseline = replace(self.cohort, name="baseline", timepoint=0)
        results = pd.concat(
            [self.analyze_cohort(self.cohort), self.analyze_cohort(baseline)],
            ignore_index=True,
        )
        with self.database.connect() as connection:
            with connection:
                connection.execute("DELETE FROM analysis_results")
                connection.executemany(
                    "INSERT INTO analysis_results VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    results.itertuples(index=False, name=None),
                )
        return results
