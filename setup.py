import os

import setuptools  # type:ignore

with open("README.md", "r") as fh:
    long_description = fh.read()

with open(os.path.join('pyais', '__init__.py')) as f:
    for line in f:
        if line.strip().startswith('__version__'):
            VERSION = line.split('=')[1].strip()[1:-1].strip()
            break

setuptools.setup(
    name="pyais",
    version=VERSION,
    author="Leon Morten Richter",
    author_email="leon.morten@gmail.com",
    description="Ais message decoding",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/M0r13n/pyais",
    license="MIT",
    packages=setuptools.find_packages(),
    package_data={
        "pyais": ["py.typed"]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Communications",
        "Topic :: System :: Networking",
        "Typing :: Typed",
    ],
    keywords=["AIS", "ship", "decoding", "nmea"],
    python_requires='>=3.6',
    install_requires=[
        "bitarray",
        "attrs"
    ],
    entry_points={
        "console_scripts": [
            'ais-decode=pyais.main:main'
        ]
    }
)
