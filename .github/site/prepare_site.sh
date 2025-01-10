#!/bin/bash

# Exit on any error
set -e

python .github/scripts/others/check_files.py

echo "Files checked and remove large files successfully!"

# Create docs directory if it doesn't exist
mkdir -p docs

# Copy markdown files to docs directory
# Enable extended globbing if needed
shopt -s extglob
cp -r !(docs) docs/
rm -f docs/CODE_OF_CONDUCT.md
rm -f docs/CONTRIBUTING.md

# Copy all files from .github/site to root directory
cp -r .github/site/* ./

echo "Files copied successfully!"
