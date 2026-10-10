from teiko.database import Database
from teiko.repository import AnalysisRepository


def test_frequency_table_uses_server_side_pagination(pipeline_db):
    repository = AnalysisRepository(Database(pipeline_db))
    first_page, page_count = repository.frequency_page(0, 15)

    assert len(first_page) == 15
    assert page_count == 3500
    assert first_page.iloc[0]["sample"] == "sample00000"


def test_frequency_table_filters_and_sorts_safely(pipeline_db):
    repository = AnalysisRepository(Database(pipeline_db))
    frame, page_count = repository.frequency_page(
        page=0,
        page_size=10,
        sort_column="percentage",
        sort_direction="desc",
        sample_search="sample00000",
        population="b_cell",
    )

    assert page_count == 1
    assert len(frame) == 1
    assert frame.iloc[0]["population"] == "b_cell"


def test_invalid_sort_column_is_not_interpolated(pipeline_db):
    repository = AnalysisRepository(Database(pipeline_db))
    frame, _ = repository.frequency_page(
        page=0,
        page_size=5,
        sort_column="sample; DROP TABLE samples",
    )

    assert len(frame) == 5
    assert repository.overview()["samples"] == 10500
