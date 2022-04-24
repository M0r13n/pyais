run_tests:
	pytest --cov=pyais tests/

flake:
	flake8

.PHONY: build
build:
	rm -rf dist/ && rm -rf build/ && python setup.py sdist bdist_wheel

check-build:
	twine check dist/*

type-check:
	mypy ./pyais

clean:
	rm -rf .mypy_cache
	rm -rf build
	rm -rf dist
	rm coverage.xml
	rm .coverage

test: run_tests flake type-check

install:
	pip install wheel
	pip install -U .[dev]
