import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_required_root_scripts_run_without_arguments(tmp_path):
    database = tmp_path / "cli.db"
    environment = {
        **os.environ,
        "CELL_COUNT_CSV": str(ROOT / "cell-count.csv"),
        "CELL_COUNT_DB": str(database),
    }

    load = subprocess.run(
        [sys.executable, "load_data.py"],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    analysis = subprocess.run(
        [sys.executable, "analyze.py"],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Loaded 3,500 subjects" in load.stdout
    assert "all_timepoints" in analysis.stdout
    assert "baseline" in analysis.stdout
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM analysis_results").fetchone()[0] == 10
