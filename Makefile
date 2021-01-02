init:
	pip install -r requirements_dev.txt

run_tests:
	nosetests -v  --with-coverage --cover-package pyais tests/*.py

flake:
	python -m flake8

.PHONY: build
build:
	rm -rf dist/ && rm -rf build/ && python setup.py sdist bdist_wheel

check-build:
	twine check dist/*

type-check:
	mypy .

test: run_tests flake type-check