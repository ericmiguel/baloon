"""Baloon: BLN polygon conversion toolkit (formerly blnconverter).

Provides utilities to parse Golden Software / Surfer BLN files and convert them to
common geospatial vector formats (Shapefile / GeoJSON).

Backwards compatibility: importing `blnconverter` still works (shim module).
"""

__all__ = [
    "BLNParseError",
    "BLNRecord",
    "convert_file",
    "convert_path",
    "list_formats",
    "parse_bln",
]

__version__ = "2.1.0"

from .core import BLNParseError, BLNRecord, convert_file, convert_path, parse_bln
from .formats import list_formats
