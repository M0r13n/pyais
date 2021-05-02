############
Installation
############

``pyais`` is compatible with Python 3.6.9+.

Use :command:`pip` to install the latest stable version of ``pyais``:

.. code-block:: console

   $ pip install --upgrade pyais

The current development version is available on `github
<https://github.com/M0r13n/pyais>`__. Use :command:`git` and
:command:`python setup.py` to install it:

.. code-block:: console

   $ git clone https://github.com/M0r13n/pyais.git
   $ cd pyais
   $ sudo python setup.py install


## Known problems

During installation, you may encounter problems due to missing header files. The error looks like this:

````sh
...

    bitarray/_bitarray.c:13:10: fatal error: Python.h: No such file or directory
       13 | #include "Python.h"
          |          ^~~~~~~~~~
    compilation terminated.
    error: command 'x86_64-linux-gnu-gcc' failed with exit status 1

...

````

In  order to solve this issue, you need to install header files and static libraries for python dev:

````sh
$ sudo apt install python3-dev
````

#### Installation in Visualstudio

You may encounter the error:

````sh
    ...
    error: Microsoft Visual C++ 14.0 or greater is required. Get it with "Microsoft C++ Build Tools
    ...
````

To solve this issue, you need to:

1. get the up to date buildstools from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. install them via the included installation manager app
3. use default options during installation
4. install Pyais via pip: `pip install pyais`
