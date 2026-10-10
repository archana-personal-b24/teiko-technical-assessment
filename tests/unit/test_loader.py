import sqlite3
from contextlib import closing

import pytest

from teiko.loader import CellCountLoader

HEADER = (
    "project,subject,condition,age,sex,treatment,response,sample,sample_type,"
    "time_from_treatment_start,b_cell,cd8_t_cell,cd4_t_cell,nk_cell,monocyte\n"
)
ROW = "p1,s1,melanoma,50,M,miraclib,yes,x1,PBMC,0,1,2,3,4,5\n"


def test_loader_normalizes_and_loads_one_row(tmp_path):
    source = tmp_path / "input.csv"
    source.write_text(HEADER + ROW, encoding="utf-8")
    target = tmp_path / "result.db"
    report = CellCountLoader(target).load(source)
    assert (report.subjects, report.samples, report.cell_counts) == (1, 1, 5)
    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute("SELECT SUM(count) FROM cell_counts").fetchone()[0] == 15
        assert connection.execute("SELECT ROUND(SUM(percentage),8) FROM sample_frequencies").fetchone()[0] == 100


@pytest.mark.parametrize(
    "row,message",
    [
        (ROW.replace("x1", ""), "Missing or duplicate sample"),
        (ROW.replace(",1,2,3,4,5", ",-1,2,3,4,5"), "Invalid cell counts"),
        (ROW.replace(",yes,", ",maybe,"), "Invalid subject metadata"),
    ],
)
def test_loader_rejects_invalid_rows(tmp_path, row, message):
    source = tmp_path / "bad.csv"
    source.write_text(HEADER + row, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        CellCountLoader(tmp_path / "bad.db").load(source)
    assert not (tmp_path / "bad.db").exists()


def test_failed_reload_preserves_existing_database(tmp_path):
    good = tmp_path / "good.csv"
    good.write_text(HEADER + ROW, encoding="utf-8")
    target = tmp_path / "result.db"
    loader = CellCountLoader(target)
    loader.load(good)
    bad = tmp_path / "bad.csv"
    bad.write_text(HEADER + ROW + ROW, encoding="utf-8")
    with pytest.raises(ValueError):
        loader.load(bad)
    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM samples").fetchone()[0] == 1
