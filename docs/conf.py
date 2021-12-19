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
import os
import shutil
import subprocess
import sys
#sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
sys.path.append(os.path.abspath('ext'))


# -- Project information -----------------------------------------------------

project = 'Being'
copyright = '2021, Alexander Theler'
author = 'Alexander Theler'
github_url = 'https://github.com'
github_repo_org = 'rauc-lab'
github_repo_name = 'being'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.napoleon',
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
    'sphinx.ext.graphviz',
    'sphinx.ext.intersphinx',
    'matplotlib.sphinxext.plot_directive',
    'formatted_autodoc',
    'sphinx_js',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# These paths are either relative to html_static_path
# or fully qualified paths (eg. https://...)
html_css_files = [
    'custom.css',
]


# -- Options extensions ------------------------------------------------------

# napoleon configuration
napoleon_google_docstring = True
#napoleon_use_param = False
#napoleon_use_ivar = True

# autodoc configuration
autoclass_content = 'both'
autodoc_member_order = 'bysource'  # alphabetical, bysource, groupwise
add_module_names = False

# todo configuration
todo_include_todos = True

# intersphinx configuration
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
    'canopen': ('https://canopen.readthedocs.io/en/latest/', None),
}

# matplotlib plotting configuration
plot_include_source = True
plot_pre_code = """
import numpy as np
import matplotlib.pyplot as plt


#plt.rcParams['axes.spines.top'] = False
#plt.rcParams['axes.spines.right'] = False
#plt.rcParams['axes.spines.bottom'] = False
#plt.rcParams['axes.spines.left'] = False


def prettify_plot(ax=None):
    if ax is None:
        ax = plt.gca()

    ax.xaxis.set_ticks_position('none')
    ax.yaxis.set_ticks_position('none')
"""

plot_rcparams = {
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.spines.bottom': False,
    'axes.spines.left': False,
}

# sphinx-js configuration
if shutil.which('jsdoc') is None:
    print('jsdoc is not install')
    print('Trying to install it')
    subprocess.run(['npm', 'install', '-g', 'jsdoc'], check=True)

#js_source_path = '../being/web/static/js'
js_source_path = [
    '../being/web/static/js',
    '../being/web/static/components',
]
root_for_relative_js_paths = '../being/web/static'
jsdoc_config_path = 'conf.json'


# -- Misc --------------------------------------------------------------------
# RST prolog for global href links
rst_prolog = """
.. _Klang: http://github.com/atheler/klang
"""
