.PHONY: setup pipeline dashboard test test-unit test-integration format lint typecheck audit check

setup:
	python -m pip install -r requirements-dev.txt

pipeline:
	python load_data.py
	python analyze.py

dashboard:
	python app.py

test:
	python -m pytest

test-unit:
	python -m pytest -q tests/unit

test-integration:
	python -m pytest -q tests/integration

format:
	python -m ruff format .

lint:
	python -m ruff check .
	python -m ruff format --check .

typecheck:
	python -m mypy teiko load_data.py analyze.py app.py

audit:
	python -m pip_audit -r requirements.txt

check: lint typecheck pipeline test audit
