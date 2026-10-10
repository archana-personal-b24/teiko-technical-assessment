from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from teiko.database import Database

RESULT_COLUMNS = ["population","n_responders","n_nonresponders","mean_responder","mean_nonresponder","mean_difference","t_statistic","p_value","adjusted_p_value","cohens_d","significant"]


@dataclass(frozen=True)
class CohortDefinition:
    condition: str = "melanoma"
    treatment: str = "miraclib"
    sample_type: str = "PBMC"


class ResponseAnalyzer:
    def __init__(self, database: Database, alpha: float = 0.05, cohort: CohortDefinition = CohortDefinition()):
        if not 0 < alpha < 1: raise ValueError("alpha must be between 0 and 1")
        self.database, self.alpha, self.cohort = database, alpha, cohort

    @staticmethod
    def adjust_pvalues(p_values: list[float]) -> np.ndarray:
        p=np.asarray(p_values,dtype=float)
        if p.ndim!=1 or len(p)==0 or np.any((p<0)|(p>1)|np.isnan(p)): raise ValueError("p-values must be a non-empty 1D sequence in [0, 1]")
        order=np.argsort(p); ranked=p[order]
        adjusted=np.minimum.accumulate((ranked*len(p)/np.arange(1,len(p)+1))[::-1])[::-1]
        result=np.empty_like(adjusted); result[order]=np.clip(adjusted,0,1)
        return result

    @staticmethod
    def cohens_d(first: np.ndarray, second: np.ndarray) -> float:
        if len(first)<2 or len(second)<2: raise ValueError("Cohen's d requires at least two observations per group")
        pooled=np.sqrt(((len(first)-1)*first.var(ddof=1)+(len(second)-1)*second.var(ddof=1))/(len(first)+len(second)-2))
        return float((first.mean()-second.mean())/pooled) if pooled else 0.0

    def observations(self) -> pd.DataFrame:
        query="""SELECT s.subject_id,s.response,f.population,f.percentage FROM sample_frequencies f JOIN samples x ON x.sample_id=f.sample JOIN subjects s ON s.subject_id=x.subject_id WHERE s.condition=? AND s.treatment=? AND x.sample_type=? AND s.response IN ('yes','no')"""
        with self.database.connect() as connection:
            return pd.read_sql_query(query,connection,params=(self.cohort.condition,self.cohort.treatment,self.cohort.sample_type))

    def analyze(self, observations: pd.DataFrame) -> pd.DataFrame:
        required={"subject_id","response","population","percentage"}
        if observations.empty: raise ValueError("Analysis cohort is empty")
        if not required.issubset(observations.columns): raise ValueError(f"Observations require columns: {sorted(required)}")
        means=observations.groupby(["subject_id","response","population"],as_index=False)["percentage"].mean()
        rows=[]; p_values=[]
        for population,frame in means.groupby("population",sort=True):
            yes=frame.loc[frame.response=="yes","percentage"].to_numpy(float); no=frame.loc[frame.response=="no","percentage"].to_numpy(float)
            if len(yes)<2 or len(no)<2: raise ValueError(f"Population {population} has fewer than two subjects per group")
            test=stats.ttest_ind(yes,no,equal_var=False); p_values.append(float(test.pvalue))
            rows.append([population,len(yes),len(no),yes.mean(),no.mean(),yes.mean()-no.mean(),test.statistic,test.pvalue,0.0,self.cohens_d(yes,no),0])
        for row,adjusted in zip(rows,self.adjust_pvalues(p_values)): row[8],row[10]=float(adjusted),int(adjusted<self.alpha)
        return pd.DataFrame(rows,columns=RESULT_COLUMNS)

    def run_and_persist(self) -> pd.DataFrame:
        results=self.analyze(self.observations())
        with self.database.connect() as connection:
            with connection:
                connection.execute("DELETE FROM analysis_results")
                connection.executemany("INSERT INTO analysis_results VALUES (?,?,?,?,?,?,?,?,?,?,?)",results.itertuples(index=False,name=None))
        return results
