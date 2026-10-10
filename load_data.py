"""Required zero-argument entry point for loading the source data."""

from teiko.config import Settings
from teiko.loader import CellCountLoader


def main() -> None:
    settings = Settings.from_environment()
    report = CellCountLoader(settings.database_path).load(settings.csv_path)
    print(f"Loaded {report.subjects:,} subjects, {report.samples:,} samples, "
          f"and {report.cell_counts:,} counts into {settings.database_path.name}")


if __name__ == "__main__":
    main()
