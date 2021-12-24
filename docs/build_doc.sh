#!/bin/bash
#rm -r _build

# Generate API doc from source code
rm -r "api reference core"
sphinx-apidoc --force --module-first --output-dir "api reference core" "../being"
rm -r "api reference web"
python3 js-apidoc.py --output-dir "api reference web" "../being/web/static/js" "../being/web/static/components"

make html

# Overwrite custom.css in any case
rm _build/html/_static/custom.css
cp _static/custom.css _build/html/_static

#open _build/html/index.html
