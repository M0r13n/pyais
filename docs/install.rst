Installation
============

Requirements
------------

- Python 3.9 or later (CPython or PyPy)

Install from PyPI
-----------------

.. code-block:: console

   $ pip install pyais

Install the development version
-------------------------------

.. code-block:: console

   $ git clone https://github.com/M0r13n/pyais.git
   $ cd pyais
   $ pip install -e ".[test]"

Verify a release
----------------

Every GitHub release includes a ``SHA256SUMS`` file with checksums for the
PyPI artifacts. To verify your download:

.. code-block:: console

   $ VERSION=3.3.1
   $ pip download pyais==$VERSION --no-deps -d pyais-dist && cd pyais-dist
   $ curl -LO https://github.com/M0r13n/pyais/releases/download/v$VERSION/SHA256SUMS
   $ sha256sum -c --ignore-missing SHA256SUMS

Every file should report ``OK``.

Troubleshooting
---------------

Missing Python headers (Linux)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you see ``fatal error: Python.h: No such file or directory`` during
installation, install the Python development headers:

.. code-block:: console

   $ sudo apt install python3-dev

Microsoft Visual C++ (Windows)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``bitarray`` dependency requires a C compiler. Install the
`Microsoft C++ Build Tools <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_
and select "Desktop development with C++" during installation. Then:

.. code-block:: console

   > pip install pyais

Docker
------

Build and run a container:

.. code-block:: console

   $ docker build . -t pyais
   $ docker run -it --rm pyais /bin/bash

Run an example inside the container:

.. code-block:: console

   $ python ./examples/live_stream.py
