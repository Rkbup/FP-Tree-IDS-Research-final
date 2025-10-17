# Makefile for FP-Tree-IDS-Research-final (Linux)

.PHONY: all venv install run-main run-synthetic monitor extract clean docker-build

all: venv install

venv:
	python3.13 -m venv .venv

install:
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

run-main:
	. .venv/bin/activate && python experiments/main_experiment.py

run-synthetic:
	. .venv/bin/activate && python experiments/synthetic_full_experiment.py

monitor:
	tail -n 30 -F logs/*.log

extract:
	mkdir -p results-final/tables results-final/figures
	cp results/tables/* results-final/tables/ || true
	cp results/figures/* results-final/figures/ || true

clean:
	rm -rf logs/*.log results-final/*

docker-build:
	docker build -t fp-tree-ids:latest .
