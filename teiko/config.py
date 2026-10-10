from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    root: Path
    csv_path: Path
    database_path: Path
    alpha: float = 0.05

    @classmethod
    def from_environment(cls) -> Settings:
        root = Path(__file__).resolve().parents[1]
        return cls(
            root,
            Path(os.environ.get("CELL_COUNT_CSV", root / "cell-count.csv")),
            Path(os.environ.get("CELL_COUNT_DB", root / "cell_counts.db")),
            float(os.environ.get("ANALYSIS_ALPHA", "0.05")),
        )
