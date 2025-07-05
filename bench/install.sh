#!/bin/bash

set -e

echo "Using python: $(which python3)"

mkdir -p build
cd build

if [ ! -d "libais" ]; then
    git clone git@github.com:schwehr/libais.git
fi

cd libais
uv pip install setuptools six
python setup.py build
python setup.py install

echo "Installed libais."
