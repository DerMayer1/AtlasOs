.PHONY: install test lint reproduce

install:
	pip install -e .[dev]

test:
	pytest --cov=atlas

lint:
	ruff check .

# Phase 2 will regenerate validation outputs from frozen snapshots here (PRD G1).
reproduce:
	pytest tests/test_impairment_engine.py::test_same_seed_bit_identical_artifacts -q
