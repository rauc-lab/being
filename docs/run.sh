#!/bin/bash
#rm -r _build
sphinx-apidoc -f -o reference ../being
#sphinx-apidoc -f -o docs/source projectdir
#sphinx-apidoc -f -o reference ../being
make html
rm _build/html/_static/custom.css
cp _static/custom.css _build/html/_static
#open _build/html/index.html
