<div align="center">
  <img src="assets/logo.png" alt="Baloon logo" width="400"/>

<br><br>
<a href="https://pypi.org/project/baloon/">
<img src="https://badge.fury.io/py/baloon.svg" alt="PyPI version"/>
</a>
<a href="https://www.python.org/downloads/">
<img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"/>
</a>

</div>

Baloon is a command-line tool and Python library for converting between geospatial vector formats. Convert BLN, Shapefile, GeoJSON, KML, GeoPackage, and SVG files quickly and easily.

## Features

-   **CLI and Python API**: Use on the command line or import in your scripts
-   **Single files and directories**: Convert one file or entire folders (recursive)
-   **Any-to-any conversion**: Convert between supported formats
    -   BLN is read-only (input only); SVG is write-only (output only)
-   **Supported formats**: BLN, Shapefile (.shp), GeoJSON (.geojson/.json), KML (.kml), GeoPackage (.gpkg), SVG (.svg)

## Installation

```bash
# Using uv (recommended)
uv add baloon

# Using pip
pip install baloon
```

## Usage

### Command Line

Note: Options must come before positional arguments.

Basics (auto-detect by extension):

```bash
uv run baloon input.bln output.geojson
uv run baloon data.geojson output.shp
uv run baloon map.kml output.gpkg
```

Help and usage:

```bash
uv run baloon --help
```

Explicit formats (ambiguous extensions or forcing a format):

```bash
# When extensions are ambiguous
uv run baloon --input-format bln --output-format geojson input.txt output.json

# Force output format regardless of extension
uv run baloon --output-format shp input.geojson output.data
```

Overwrite behavior (single file conversions):

```bash
# Overwrite existing output file
uv run baloon --overwrite input.bln output.geojson
```

Directory conversions (recursive):

```bash
# Convert all supported readable files under ./data to GeoJSON in ./out-geojson
uv run baloon --output-format geojson ./data ./out-geojson

# Convert all supported readable files under ./project to Shapefile in ./out-shp
uv run baloon --output-format shp ./project ./out-shp
```

Notes for directory conversions:

-   The output path must be a directory; it will be created if it does not exist.
-   Input formats are auto-detected per file. Unsupported formats and write-only inputs (e.g., SVG) are skipped with a warning.
-   The relative directory structure is preserved in the output.
-   Existing output files are overwritten.

Advanced bash loops (custom naming and filters):

```bash
# Convert only KML files to GPKG, preserving stems next to inputs
find data -type f -name '*.kml' -print0 | while IFS= read -r -d '' f; do
  out="${f%.*}.gpkg"
  uv run baloon "$f" "$out"
done

# Convert mixed inputs to GeoJSON into ./out, mirroring structure
find data -type f \( -name '*.bln' -o -name '*.kml' -o -name '*.shp' -o -name '*.gpkg' -o -name '*.geojson' -o -name '*.json' \) -print0 \
| while IFS= read -r -d '' f; do
  rel="${f#data/}";
  base="${rel%.*}";
  mkdir -p "out/$(dirname "$base")";
  uv run baloon "$f" "out/${base}.geojson"
done

# Convert to multiple target formats (two passes)
for fmt in geojson shp; do
  uv run baloon --output-format "$fmt" ./data "./out-$fmt"
done
```

Path tips:

-   Quote paths with spaces: `uv run baloon "My Data/input.kml" "Out/maps.gpkg"`.
-   Shapefile outputs create a set of files (.shp, .shx, .dbf, etc.) next to the .shp path you provide.
-   BLN is input-only; SVG is output-only. Reading SVG in single-file mode will error; in directory mode SVG inputs are skipped.

### Python API

**Quick conversions (any format → any format):**

```python
import baloon

# Prefer simple aliases: convert, convert_dir, read_bln

# Convert single file (auto-detects by extension)
baloon.convert('input.bln', 'output.geojson')
baloon.convert('data.geojson', 'boundaries.shp')

# For ambiguous extensions, prefer the CLI with --input-format/--output-format
# (BLN is input-only; SVG is output-only)
```

**Batch convert directories (Python API):**

```python
import baloon

# Convert all supported readable files in a directory to GeoJSON
# - Preserves relative structure
# - Skips write-only inputs (e.g., SVG)
baloon.convert_dir('./data/', 'geojson')
```

**Working with BLN data:**

```python
from baloon import read_bln
from pathlib import Path

# Parse BLN file
records = read_bln(Path('boundary.bln'))
print(f'Found {len(records)} coordinate points')

# Access coordinates
for record in records:
    print(f'Point: {record.x}, {record.y}')
```

**Load any format as GeoDataFrame:**

```python
from baloon.formats import load_any
from pathlib import Path

# Load any supported format as GeoDataFrame
gdf = load_any(Path('data.geojson'))  # or .shp, .kml, .gpkg, .bln
print(f'Loaded {len(gdf)} features')
print(gdf.head())
```

## Supported Formats

| Format         | Extension           | Read | Write | Description                   |
| -------------- | ------------------- | ---- | ----- | ----------------------------- |
| **BLN**        | `.bln`              | ✅   | ❌    | Golden Software polygon files |
| **Shapefile**  | `.shp`              | ✅   | ✅    | ESRI standard with components |
| **GeoJSON**    | `.geojson`, `.json` | ✅   | ✅    | RFC 7946 feature collections  |
| **KML**        | `.kml`              | ✅   | ✅    | Google Earth format           |
| **GeoPackage** | `.gpkg`             | ✅   | ✅    | OGC SQLite-based format       |
| **SVG**        | `.svg`              | ❌   | ✅    | Scalable vector graphics      |

## Tips

-   If your file has a non-standard extension, use CLI format flags:
    -   `uv run baloon --input-format bln --output-format geojson input.txt output.txt`
-   Use the Python API for batch conversions and programmatic workflows.

## License

This project is licensed under the GPL-3.0-or-later. See the LICENSE file for details.
