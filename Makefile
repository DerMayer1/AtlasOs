.PHONY: install test lint reproduce

install:
	pip install -e .[dev]

test:
	pytest --cov=atlas

lint:
	ruff check .

reproduce:
	pytest tests/test_impairment_engine.py::test_same_seed_bit_identical_artifacts -q

validation-report:
	python scripts/validation_report.py
