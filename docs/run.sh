#!/bin/bash
sphinx-apidoc -f -o reference ../being
#sphinx-apidoc -f -o docs/source projectdir
#sphinx-apidoc -f -o reference ../being
make html
