from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from teiko.database import Database

POPULATIONS = ("b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte")
REQUIRED_COLUMNS = frozenset(
    {
        "project",
        "subject",
        "condition",
        "age",
        "sex",
        "treatment",
        "response",
        "sample",
        "sample_type",
        "time_from_treatment_start",
        *POPULATIONS,
    }
)


@dataclass(frozen=True)
class LoadReport:
    subjects: int
    samples: int
    cell_counts: int


class CellCountLoader:
    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)

    @staticmethod
    def _subject_record(row: Mapping[str, str], line: int) -> tuple[object, ...]:
        try:
            response = row["response"].strip().lower() or None
            record = (
                row["subject"].strip(),
                row["project"].strip(),
                row["condition"].strip().lower(),
                int(row["age"]),
                row["sex"].strip().upper(),
                row["treatment"].strip().lower(),
                response,
            )
        except (KeyError, ValueError) as error:
            raise ValueError(f"Invalid subject metadata at CSV line {line}: {error}") from error
        if not record[0] or record[3] < 0 or record[4] not in {"M", "F"} or response not in {None, "yes", "no"}:
            raise ValueError(f"Invalid subject metadata at CSV line {line}")
        return record

    def load(self, csv_path: Path) -> LoadReport:
        csv_path = Path(csv_path)
        if not csv_path.is_file():
            raise FileNotFoundError(f"Input file not found: {csv_path}")
        subjects: dict[str, tuple[object, ...]] = {}
        samples: list[tuple[object, ...]] = []
        counts: list[tuple[object, ...]] = []
        seen: set[str] = set()
        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
            for line, row in enumerate(reader, start=2):
                record = self._subject_record(row, line)
                subject = str(record[0])
                if subject in subjects and subjects[subject] != record:
                    raise ValueError(f"Inconsistent metadata for {subject} at CSV line {line}")
                subjects[subject] = record
                sample = row["sample"].strip()
                if not sample or sample in seen:
                    raise ValueError(f"Missing or duplicate sample at CSV line {line}: {sample}")
                seen.add(sample)
                try:
                    time = int(row["time_from_treatment_start"])
                    values = [int(row[p]) for p in POPULATIONS]
                except ValueError as error:
                    raise ValueError(f"Non-integer value at CSV line {line}: {error}") from error
                if any(v < 0 for v in values) or sum(values) == 0:
                    raise ValueError(f"Invalid cell counts at CSV line {line}")
                samples.append((sample, subject, row["sample_type"].strip().upper(), time))
                counts.extend((sample, p, v) for p, v in zip(POPULATIONS, values, strict=False))
        if not samples:
            raise ValueError("Input CSV contains no data rows")
        temporary = self.database_path.with_suffix(self.database_path.suffix + ".tmp")
        temporary.unlink(missing_ok=True)
        database = Database(temporary)
        try:
            database.initialize()
            with database.connect() as connection, connection:
                connection.executemany("INSERT INTO subjects VALUES (?,?,?,?,?,?,?)", subjects.values())
                connection.executemany("INSERT INTO samples VALUES (?,?,?,?)", samples)
                connection.executemany("INSERT INTO cell_counts VALUES (?,?,?)", counts)
            database.integrity_check()
            temporary.replace(self.database_path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return LoadReport(len(subjects), len(samples), len(counts))
