PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python

.PHONY: setup pipeline test dashboard

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install -r requirements.txt

pipeline:
	$(VENV_PYTHON) load_data.py
	$(VENV_PYTHON) analysis.py
	$(VENV_PYTHON) -m pytest -q

test:
	$(VENV_PYTHON) -m pytest -q

dashboard:
	$(VENV_PYTHON) -m streamlit run dashboard.py --server.address=0.0.0.0
