# Baloon 🎈

> **Modern geospatial file converter** - Transform BLN polygon files into contemporary formats

[![Tests](https://github.com/your-username/baloon/workflows/Tests/badge.svg)](https://github.com/your-username/baloon/actions)
[![PyPI version](https://badge.fury.io/py/baloon.svg)](https://pypi.org/project/baloon/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Baloon (formerly BLN-Converter) is a professional-grade command-line tool for converting geospatial polygon files between formats. Originally designed for legacy Golden Software BLN files, it has evolved into a modern, extensible converter supporting multiple vector formats.

## ✨ Features

### Multi-Format Support
- **Input formats**: BLN, Shapefile, GeoJSON
- **Output formats**: Shapefile, GeoJSON, SVG (preview renderer)
- **Extensible**: Plugin-style format registry for easy expansion

### Modern Architecture
- **Type-safe**: Full native Python 3.10+ type annotations
- **CLI excellence**: Beautiful Rich-powered terminal output
- **Fast**: Efficient processing with GeoPandas backend
- **Tested**: Comprehensive test coverage with pytest

### Developer Experience
- **Professional docs**: NumPy-style docstrings throughout
- **Linting**: Ruff for consistent code quality
- **CI/CD ready**: GitHub Actions integration
- **Modern build**: Hatch + pyproject.toml configuration

## 🚀 Installation

```bash
# Using uv (recommended for modern Python development)
uv add baloon

# Using pip
pip install baloon

# From source (development)
git clone https://github.com/your-username/baloon.git
cd baloon
pip install -e .
```

## 💻 Usage

### Command Line Interface

**Convert a single file to multiple formats:**
```bash
baloon convert boundary.bln --to geojson svg
```

**Batch convert entire directories:**
```bash
baloon batch ./data/ --to geojson --out ./converted/
```

**Inspect BLN file contents:**
```bash
baloon inspect polygon.bln
```

**List all supported formats:**
```bash
baloon formats
```

### Python API

```python
from baloon import parse_bln, convert_file
from pathlib import Path

# Parse BLN coordinates
records = parse_bln(Path("boundary.bln"))
print(f"Found {len(records)} coordinate points")

# Convert between formats
convert_file(
    Path("input.bln"), 
    Path("output.geojson")
)
```

## 🏗️ Format Support

| Format | Extension | Read | Write | Description |
|--------|-----------|------|-------|-------------|
| **BLN** | `.bln` | ✅ | ❌ | Golden Software polygon files |
| **Shapefile** | `.shp` | ✅ | ✅ | ESRI standard with components |
| **GeoJSON** | `.geojson`, `.json` | ✅ | ✅ | RFC 7946 feature collections |
| **SVG** | `.svg` | ❌ | ✅ | Scalable vector graphics (preview) |

## 🔧 Development

### Architecture Overview

Baloon follows modern Python development practices:

- **Core module** (`core.py`): BLN parsing and coordinate handling
- **Format registry** (`formats.py`): Pluggable reader/writer system  
- **CLI interface** (`cli.py`): Typer-based command line with Rich output
- **Type safety**: Native Python 3.10+ union syntax (`str | None`)
- **Documentation**: NumPy-style docstrings for all public APIs

### Key Design Decisions

1. **Format Registry Pattern**: Extensible plugin system for adding new formats
2. **GeoPandas Integration**: Leverage proven geospatial libraries
3. **Rich Terminal Output**: Professional CLI experience with tables and colors  
4. **Native Type Annotations**: Modern Python type system without `__future__` imports
5. **Comprehensive Testing**: Unit tests for parsing, conversion, and error handling

### Contributing

```bash
# Set up development environment
git clone https://github.com/your-username/baloon.git
cd baloon
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e ".[dev]"

# Run tests
pytest

# Code formatting and linting
ruff format .
ruff check .

# Type checking
pyright
```

Verbosity levels:

```bash
baloon convert area.geojson -t shp -v    # info
baloon convert area.geojson -t shp -vv   # debug
```

## Dependencies

- [GeoPandas](https://geopandas.org)
- [Typer](https://typer.tiangolo.com)
- [Rich](https://github.com/Textualize/rich)
- [Shapely](https://shapely.readthedocs.io)
- [Fiona](https://fiona.readthedocs.io)

## License

[MIT License](LICENSE)

## Contributing

Contributions welcome! This codebase follows a modern Python stack:

* Packaging: `pyproject.toml` + Hatch build backend
* Dependency management: `uv` (fast) or pip
* CLI: Typer + Rich
* Lint & Format: Ruff
* Static typing: Pyright (strict) + native type hints
* Tests: Pytest

### Dev quickstart

```bash
uv venv
source .venv/bin/activate
uv sync --all-extras --dev
pytest
ruff check . && ruff format --check .
pyright
```

### Pre-commit

Install hooks (optional):

```bash
uv add --dev pre-commit
pre-commit install
```

### Migration note (<=1.0.x)

Previous package name `bln-converter` and commands remain available as shims; migrate to `baloon`.
