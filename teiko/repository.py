"""Read-only, parameterized queries used by the dashboard."""

from __future__ import annotations

import math

import pandas as pd

from teiko.database import Database
from teiko.loader import POPULATIONS

FREQUENCY_COLUMNS = ("sample", "total_count", "population", "count", "percentage")


class AnalysisRepository:
    """Query interface that keeps SQL out of presentation code."""

    def __init__(self, database: Database):
        self.database = database

    def query(self, sql: str, params: tuple[object, ...] = ()) -> pd.DataFrame:
        with self.database.connect() as connection:
            return pd.read_sql_query(sql, connection, params=params)

    def overview(self) -> dict[str, int]:
        frame = self.query(
            """
            SELECT COUNT(DISTINCT x.sample_id) AS samples,
                   COUNT(DISTINCT x.subject_id) AS subjects
            FROM samples AS x
            """
        )
        return {key: int(frame.iloc[0][key]) for key in ("samples", "subjects")}

    def response_cohort(self) -> pd.DataFrame:
        return self.query(
            """
            SELECT f.population, f.percentage, s.response
            FROM sample_frequencies AS f
            JOIN samples AS x ON x.sample_id = f.sample
            JOIN subjects AS s ON s.subject_id = x.subject_id
            WHERE s.condition = 'melanoma'
              AND s.treatment = 'miraclib'
              AND x.sample_type = 'PBMC'
              AND s.response IN ('yes', 'no')
            """
        )

    def statistics(self, analysis_name: str) -> pd.DataFrame:
        return self.query(
            """
            SELECT population, n_responders, n_nonresponders,
                   mean_responder, mean_nonresponder, mean_difference,
                   t_statistic, p_value, adjusted_p_value, cohens_d, significant
            FROM analysis_results
            WHERE analysis_name = ?
            ORDER BY adjusted_p_value
            """,
            (analysis_name,),
        )

    def baseline(self) -> pd.DataFrame:
        return self.query(
            """
            SELECT s.project, s.subject_id, s.response, s.sex, x.sample_id
            FROM subjects AS s
            JOIN samples AS x USING (subject_id)
            WHERE s.condition = 'melanoma'
              AND s.treatment = 'miraclib'
              AND x.sample_type = 'PBMC'
              AND x.time_from_treatment_start = 0
            """
        )

    def male_responder_b_cell_mean(self) -> float:
        frame = self.query(
            """
            SELECT AVG(c.count) AS value
            FROM subjects AS s
            JOIN samples AS x USING (subject_id)
            JOIN cell_counts AS c USING (sample_id)
            WHERE s.condition = 'melanoma'
              AND s.sex = 'M'
              AND s.response = 'yes'
              AND x.time_from_treatment_start = 0
              AND c.population = 'b_cell'
            """
        )
        return float(frame.iloc[0, 0])

    @staticmethod
    def _frequency_filters(sample_search: str | None, population: str | None) -> tuple[str, list[object]]:
        clauses: list[str] = []
        parameters: list[object] = []
        if sample_search:
            clauses.append("sample LIKE ?")
            parameters.append(f"%{sample_search.strip()}%")
        if population in POPULATIONS:
            clauses.append("population = ?")
            parameters.append(population)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        return where, parameters

    def frequency_page(
        self,
        page: int,
        page_size: int,
        sort_column: str = "sample",
        sort_direction: str = "asc",
        sample_search: str | None = None,
        population: str | None = None,
    ) -> tuple[pd.DataFrame, int]:
        """Return one filtered page and total page count using safe sort fields."""
        if page < 0 or page_size < 1:
            raise ValueError("page must be non-negative and page_size must be positive")
        if sort_column not in FREQUENCY_COLUMNS:
            sort_column = "sample"
        direction = "DESC" if sort_direction.lower() == "desc" else "ASC"
        where, parameters = self._frequency_filters(sample_search, population)
        count = self.query(
            f"SELECT COUNT(*) AS rows FROM sample_frequencies{where}",  # noqa: S608
            tuple(parameters),
        ).iloc[0, 0]
        query = (
            f"SELECT {', '.join(FREQUENCY_COLUMNS)} FROM sample_frequencies"  # noqa: S608
            f"{where} ORDER BY {sort_column} {direction} LIMIT ? OFFSET ?"
        )
        data = self.query(
            query,
            tuple([*parameters, page_size, page * page_size]),
        )
        return data, math.ceil(int(count) / page_size)
