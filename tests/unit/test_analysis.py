import numpy as np
import pandas as pd
import pytest

from teiko.analysis import ResponseAnalyzer


def test_benjamini_hochberg_known_values():
    actual = ResponseAnalyzer.adjust_pvalues([0.01, 0.04, 0.03, 0.002])
    np.testing.assert_allclose(actual, [0.02, 0.04, 0.04, 0.008])


def test_benjamini_hochberg_rejects_invalid_values():
    with pytest.raises(ValueError, match="p-values"):
        ResponseAnalyzer.adjust_pvalues([0.1, 1.2])


def test_cohens_d_known_effect():
    effect = ResponseAnalyzer.cohens_d(np.array([2.0, 3.0, 4.0]), np.array([1.0, 2.0, 3.0]))
    assert effect == pytest.approx(1.0)


def test_analysis_averages_repeated_samples_by_subject():
    observations = pd.DataFrame({
        "subject_id": ["r1","r1","r2","r2","n1","n1","n2","n2"],
        "response": ["yes"]*4+["no"]*4,
        "population": ["b_cell"]*8,
        "percentage": [20,40,30,34,10,12,18,22],
    })
    analyzer = object.__new__(ResponseAnalyzer)
    analyzer.alpha = 0.05
    result = analyzer.analyze(observations).iloc[0]
    assert result.n_responders == 2
    assert result.n_nonresponders == 2
    assert result.mean_responder == pytest.approx(31)
    assert result.mean_nonresponder == pytest.approx(15.5)
