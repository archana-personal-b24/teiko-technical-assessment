.PHONY: setup pipeline dashboard test test-unit test-integration check

setup:
	python -m pip install -r requirements.txt

pipeline:
	python load_data.py
	python analyze.py

dashboard:
	python app.py

test:
	python -m pytest -q

test-unit:
	python -m pytest -q tests/unit

test-integration:
	python -m pytest -q tests/integration

check: pipeline test
