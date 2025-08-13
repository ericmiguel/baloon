# Baloon 🎈

> **Geospatial vector format converter** - Transform between multiple geospatial formats

[![PyPI version](https://badge.fury.io/py/baloon.svg)](https://pypi.org/project/baloon/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Baloon is a command-line tool and Python library for converting between geospatial vector formats. Convert BLN, Shapefile, GeoJSON, KML, GeoPackage, and SVG files quickly and easily.

## Features

- **Multiple formats**: BLN, Shapefile, GeoJSON, KML, GeoPackage, SVG
- **Bidirectional conversion**: Convert from any input format to any output format  
  - Note: BLN is read-only (source-only) and SVG is write-only (destination-only)
- **Batch processing**: Convert entire directories at once (Python API)
- **Command-line interface**: Simple command for quick conversions
- **Python API**: Import and use in your scripts

## Installation

```bash
# Using uv (recommended)
uv add baloon

# Using pip
pip install baloon
```

## Usage

### Command Line

Note: Options should be placed before positional arguments.

**Convert single files:**
```bash
uv run baloon input.bln output.geojson
uv run baloon data.geojson output.shp
uv run baloon --input-format bln --output-format geojson input.txt output.txt
uv run baloon --overwrite input.bln output.geojson
```

**Convert directories (recursive):**
```bash
# Convert all supported readable files under ./data to GeoJSON in ./out-geojson
uv run baloon --output-format geojson ./data ./out-geojson

# Convert all supported readable files under ./project to Shapefile in ./out-shp
uv run baloon --output-format shp ./project ./out-shp
```

Notes for directory conversions:
- The output path must be a directory; it will be created if it does not exist.
- Input formats are auto-detected per file. Unsupported formats and write-only inputs (e.g., SVG) are skipped with a warning.
- The relative directory structure is preserved in the output.
- Existing output files are overwritten.

### Python API

**Quick conversions (any format → any format):**
```python
# uv run python -c "
import baloon

# Convert single file (auto-detects formats by extension)
baloon.convert_file('input.bln', 'output.geojson')
baloon.convert_file('data.geojson', 'boundaries.shp')

# Explicitly specify formats when extensions are ambiguous
# (BLN is read-only and SVG is write-only)
baloon.convert_file('input.data', 'output.data')  # with flags via CLI only
# "
```

**Batch convert directories (Python API):**
```python
# uv run python -c "
import baloon

# Convert all supported readable files in a directory to GeoJSON
# - Preserves relative structure
# - Skips write-only inputs (e.g., SVG)
baloon.convert_path('./data/', 'geojson')
# "
```

**Working with BLN data:**
```python
# uv run python -c "
from baloon import parse_bln
from pathlib import Path

# Parse BLN file
records = parse_bln(Path('boundary.bln'))
print(f'Found {len(records)} coordinate points')

# Access coordinates
for record in records:
    print(f'Point: {record.x}, {record.y}')
# "
```

**Load any format as GeoDataFrame:**
```python
# uv run python -c "
from baloon.formats import load_any
from pathlib import Path

# Load any supported format as GeoDataFrame
gdf = load_any(Path('data.geojson'))  # or .shp, .kml, .gpkg, .bln
print(f'Loaded {len(gdf)} features')
print(gdf.head())
# "
```

## Supported Formats

| Format | Extension | Read | Write | Description |
|--------|-----------|------|-------|-------------|
| **BLN** | `.bln` | ✅ | ❌ | Golden Software polygon files |
| **Shapefile** | `.shp` | ✅ | ✅ | ESRI standard with components |
| **GeoJSON** | `.geojson`, `.json` | ✅ | ✅ | RFC 7946 feature collections |
| **KML** | `.kml` | ✅ | ✅ | Google Earth format |
| **GeoPackage** | `.gpkg` | ✅ | ✅ | OGC SQLite-based format |
| **SVG** | `.svg` | ❌ | ✅ | Scalable vector graphics |

## Tips

- If your file has a non-standard extension, use CLI format flags:
  - `uv run baloon --input-format bln --output-format geojson input.txt output.txt`
- Use the Python API for batch conversions and programmatic workflows.

## License

[MIT License](LICENSE)
