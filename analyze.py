"""Command-line entry point for the statistical analysis stage."""

from teiko.analysis import ResponseAnalyzer
from teiko.config import Settings
from teiko.database import Database


def main() -> None:
    settings = Settings.from_environment()
    if not settings.database_path.exists():
        raise FileNotFoundError("Database missing; run python load_data.py first")
    results = ResponseAnalyzer(Database(settings.database_path), settings.alpha).run_and_persist()
    print(results.to_string(index=False, float_format=lambda value: f"{value:.6g}"))


if __name__ == "__main__":
    main()
