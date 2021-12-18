#!/bin/bash
#rm -r _build

# Generate API doc from source code
rm -r reference
#sphinx-apidoc --force --module-first --output-dir reference ../being
sphinx-apidoc --force --module-first --output-dir "reference" "../being"
python3 js-apidoc.py --output-dir "web api" "../being/web/static/js" "../being/web/static/components" 

make html

# Overwrite custom.css in any case
rm _build/html/_static/custom.css
cp _static/custom.css _build/html/_static

#open _build/html/index.html
