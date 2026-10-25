# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
from pathlib import Path
import re
import os


# -- Project information -----------------------------------------------------

project = 'Pyais'
copyright = '2026, Leon Morten Richter'
author = 'Leon Morten Richter'

# The full version, including alpha/beta/rc tags
release = re.search(
    r"__version__ = '([^']+)'",
    (Path(__file__).parent.parent / 'pyais' / '__init__.py').read_text(),
).group(1)

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
]

# Add any paths that contain templates here, relative to this directory.

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'pyais'
html_theme_path = ['_themes']
html_title = 'pyais'
html_last_updated_fmt = '%b %Y'

# Read the Docs sets this; it yields <link rel="canonical"> on every page.
html_baseurl = os.environ.get('READTHEDOCS_CANONICAL_URL', '')

# Publish only what readers need.
html_copy_source = False
html_show_sourcelink = False
html_use_index = False
