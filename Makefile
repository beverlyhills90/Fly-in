ON = python3
UV = uv

.PHONY: all install run debug clean lint format

all: install lint run

install:
	$(UV) sync

run:
	$(UV) run main.py

debug:
	$(PYTHON) -m pdb main.py

clean:
	rm -rf __pycache__ .mypy_cache .pytest_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -r {} +

lint:
	
	uv run mypy . --exclude .venv --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
	uv run flake8 . --exclude=.venv
format:
	ruff format .
	ruff check --fix .