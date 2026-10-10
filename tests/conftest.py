from pathlib import Path

import pytest

from teiko.analysis import ResponseAnalyzer
from teiko.database import Database
from teiko.loader import CellCountLoader

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def pipeline_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("pipeline") / "test.db"
    CellCountLoader(path).load(ROOT / "cell-count.csv")
    ResponseAnalyzer(Database(path)).run_and_persist()
    return path
