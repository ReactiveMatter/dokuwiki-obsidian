# Dokiwiki to Obsidian

This python script converts the Dokuwiki data files to Obsidian files.

## Usage
- The `--src` argument should be the `data` folder of the DokuWiki installation and should have `pages` folder from the `.txt` files will be parsed.
- The `--dst` argument is the folder where the output will be generated.
- The `--overwrite` argument to define whether a file in destination with same name be overwritten. The values are 0 for no overwrite (default behaviour), 1 for always overwrite, 2 for overwrite if source file is newer and Markdown content hashes of both files does not match.
- Run the script


## Features
- Converts most syntax of Dokuwiki
- Supports WRAP plugin and include plugin