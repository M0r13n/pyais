run_tests:
	nosetests -v  --with-coverage --cover-package pyais tests/*.py

flake:
	flake8

.PHONY: build
build:
	rm -rf dist/ && rm -rf build/ && python setup.py sdist bdist_wheel

check-build:
	twine check dist/*

type-check:
	mypy .

test: run_tests flake type-check