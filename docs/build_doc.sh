#!/bin/bash
#rm -r _build

# Generate API doc from source code
rm -r reference
sphinx-apidoc -f -o reference ../being
# TODO: sphinx-js for JavaScript code

make html

# Overwrite custom.css in any case
rm _build/html/_static/custom.css
cp _static/custom.css _build/html/_static

#open _build/html/index.html
