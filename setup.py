import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyais",
    version="0.0.2",
    author="Leon Morten Richter",
    author_email="leon.morten@gmail.com",
    description="Ais message decoding",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/M0r13n/pyais",
    license="MIT",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Communications",
        "Topic :: System :: Networking"
    ],
    keywords=["AIS", "ship", "decoding", "nmea"],
    python_requires='>=3.6',
    install_requires=[
        "bitarray"
    ]
)
