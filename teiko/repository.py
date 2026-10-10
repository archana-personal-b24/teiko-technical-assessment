from __future__ import annotations

import pandas as pd
from teiko.database import Database


class AnalysisRepository:
    def __init__(self,database: Database): self.database=database
    def query(self,sql: str,params: tuple[object,...]=()) -> pd.DataFrame:
        with self.database.connect() as connection: return pd.read_sql_query(sql,connection,params=params)
    def frequencies(self) -> pd.DataFrame:
        return self.query("SELECT f.*,s.subject_id,s.project FROM sample_frequencies f JOIN samples x ON x.sample_id=f.sample JOIN subjects s ON s.subject_id=x.subject_id")
    def response_cohort(self) -> pd.DataFrame:
        return self.query("SELECT f.population,f.percentage,s.response FROM sample_frequencies f JOIN samples x ON x.sample_id=f.sample JOIN subjects s ON s.subject_id=x.subject_id WHERE s.condition='melanoma' AND s.treatment='miraclib' AND x.sample_type='PBMC' AND s.response IN ('yes','no')")
    def statistics(self) -> pd.DataFrame: return self.query("SELECT * FROM analysis_results ORDER BY adjusted_p_value")
    def baseline(self) -> pd.DataFrame:
        return self.query("SELECT s.project,s.subject_id,s.response,s.sex,x.sample_id FROM subjects s JOIN samples x USING(subject_id) WHERE s.condition='melanoma' AND s.treatment='miraclib' AND x.sample_type='PBMC' AND x.time_from_treatment_start=0")
    def male_responder_b_cell_mean(self) -> float:
        frame=self.query("SELECT AVG(c.count) value FROM subjects s JOIN samples x USING(subject_id) JOIN cell_counts c USING(sample_id) WHERE s.condition='melanoma' AND s.sex='M' AND s.response='yes' AND x.time_from_treatment_start=0 AND c.population='b_cell'")
        return float(frame.iloc[0,0])
