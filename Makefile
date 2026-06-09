.PHONY: lint test validate-config safety-audit check clean-artifacts

PYTHON ?= python

lint:
	$(PYTHON) -m ruff check .

test:
	$(PYTHON) -m pytest

validate-config:
	$(PYTHON) -m trading_bot validate-config --config config/default.yaml

safety-audit:
	$(PYTHON) -m trading_bot run-safety-audit --config config/default.yaml

check: lint test validate-config safety-audit

clean-artifacts:
	$(PYTHON) scripts/clean_artifacts.py
