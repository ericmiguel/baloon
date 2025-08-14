"""Baloon: Modern geospatial vector format interconverter and CLI toolkit.

Provides utilities for bidirectional conversion between various geospatial
vector formats including BLN (Golden Software), Shapefile, GeoJSON, KML,
GeoPackage, and SVG formats. Designed for professional geospatial data
workflows with a modern Python architecture.

Main capabilities:
- Multi-format support: BLN, Shapefile, GeoJSON, KML, GeoPackage, SVG
- Bidirectional conversion between supported formats
- CLI toolkit with Rich-powered terminal interface
- Python API for programmatic use
- Extensible format registry system
"""

__all__ = [
    "BLNRecord",
    "convert_file",
    "convert_path",
    "parse_bln",
    "convert",
    "convert_dir",
    "read_bln",
    "list_formats",
]

__version__ = "1.0.1"

from .core import BLNRecord
from .core import convert
from .core import convert_dir
from .core import convert_file
from .core import convert_path
from .core import parse_bln
from .core import read_bln
from .formats import list_formats
