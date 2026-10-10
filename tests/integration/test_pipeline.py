import sqlite3


def scalar(connection,sql): return connection.execute(sql).fetchone()[0]


def test_full_pipeline_cardinality_and_integrity(pipeline_db):
    with sqlite3.connect(pipeline_db) as connection:
        assert scalar(connection,"PRAGMA integrity_check")=="ok"
        assert scalar(connection,"SELECT COUNT(*) FROM samples")==10500
        assert scalar(connection,"SELECT COUNT(*) FROM cell_counts")==52500
        deviation=scalar(connection,"SELECT MAX(ABS(total-100.0)) FROM (SELECT sample,SUM(percentage) total FROM sample_frequencies GROUP BY sample)")
        assert deviation<1e-9


def test_full_pipeline_business_answers(pipeline_db):
    with sqlite3.connect(pipeline_db) as connection:
        baseline=scalar(connection,"SELECT COUNT(*) FROM subjects s JOIN samples x USING(subject_id) WHERE condition='melanoma' AND treatment='miraclib' AND sample_type='PBMC' AND time_from_treatment_start=0")
        mean=scalar(connection,"SELECT AVG(c.count) FROM subjects s JOIN samples x USING(subject_id) JOIN cell_counts c USING(sample_id) WHERE condition='melanoma' AND sex='M' AND response='yes' AND time_from_treatment_start=0 AND population='b_cell'")
        significant=connection.execute(
            "SELECT population FROM analysis_results "
            "WHERE analysis_name='all_timepoints' AND significant=1"
        ).fetchall()
    assert baseline==656
    assert round(mean,2)==10206.15
    assert significant==[("cd4_t_cell",)]
