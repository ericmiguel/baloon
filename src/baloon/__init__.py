"""Baloon: Modern geospatial vector format interconverter and CLI toolkit.

Provides utilities for bidirectional conversion between various geospatial vector formats
including BLN (Golden Software), Shapefile, GeoJSON, KML, GeoPackage, and SVG formats.
Designed for professional geospatial data workflows with a modern Python architecture.

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
    "list_formats",
    "parse_bln",
]

__version__ = "2.1.0"

from .core import BLNRecord
from .core import convert_file
from .core import convert_path
from .core import parse_bln
from .formats import list_formats
