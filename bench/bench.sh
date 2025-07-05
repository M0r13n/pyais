#!/bin/bash

set -e

echo "Using python: $(which python3)"
python --version

echo ">>> Bench pyais"
python bench_pyais.py

echo ">>> Bench libais"
python bench_libais.py
