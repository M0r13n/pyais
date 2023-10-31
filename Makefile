run_tests:
	pytest --cov=pyais tests/

flake:
	flake8

.PHONY: build
build:
	rm -rf dist
	rm -rf build
	python -m build

check-build:
	twine check dist/*

type-check:
	mypy ./pyais --strict

clean:
	rm -rf .mypy_cache
	rm -rf build
	rm -rf dist
	rm -f coverage.xml
	rm -f .coverage

ensure-no-print:
	grep -r --exclude main.py --exclude '*.pyc' -i 'print(' ./pyais && (echo "Debug print statement found"; exit 1)||true

test: run_tests flake type-check ensure-no-print

install:
	pip install -U setuptools wheel build
	pip install -U -e .[dev]
