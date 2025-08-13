"""Core geospatial data processing functionality for Baloon.

This module provides the fundamental data structures and algorithms for parsing
various geospatial polygon files and converting them between standard formats.
Supports BLN (Golden Software), Shapefile, GeoJSON, KML, GeoPackage, and SVG formats.

Classes
-------
BLNRecord
    Represents a single coordinate point from a BLN file.

Functions
---------
parse_bln
    Parse a BLN polygon file into coordinate records.
convert_file
    Convert between any supported geospatial formats.
convert_path
    Convert geospatial file(s) from a path (file or directory).

Notes
-----
While originally designed for BLN (Golden Software) files containing polygon
boundary data used in geological and mining applications, this module now supports
bidirectional conversion between multiple modern geospatial vector formats.

All dependencies (GeoPandas, Shapely) are required and imported directly for
fail-fast behavior. Semantic exceptions provide clear error messages.
"""

from collections.abc import Iterator
from dataclasses import dataclass
import logging
from pathlib import Path

from .exceptions import GeometryError


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BLNRecord:
    """Represents a single coordinate point from a BLN polygon file.

    BLN files store polygon boundaries as sequences of coordinate pairs.
    Each record represents one vertex of the polygon boundary.

    Attributes
    ----------
    x : float
        X-coordinate (typically longitude in geographic systems).
    y : float
        Y-coordinate (typically latitude in geographic systems).

    Examples
    --------
    >>> record = BLNRecord(x=-122.4194, y=37.7749)  # San Francisco
    >>> print(f"Point: ({record.x}, {record.y})")
    Point: (-122.4194, 37.7749)
    """

    x: float
    y: float


def _iter_lines(path: Path) -> Iterator[str]:
    """Iterate over non-empty lines in a text file.

    Parameters
    ----------
    path : Path
        Path to the text file to read.

    Yields
    ------
    str
        Non-empty, stripped lines from the file.

    Notes
    -----
    Uses UTF-8 encoding with error recovery to handle malformed files.
    Empty lines and pure whitespace lines are automatically skipped.
    """
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            yield line


def parse_bln(path: Path) -> list[BLNRecord]:
    """Parse a BLN polygon file into coordinate records.

    Parses Golden Software BLN format files, which contain polygon boundary
    data as coordinate pairs. Supports both comma and tab-separated values.

    Assumes coordinates are geographic (longitude, latitude) in degrees
    and validates that longitude is within [-180, 180] and latitude within
    [-90, 90]. Lines with non-numeric values are ignored (treated as headers),
    and out-of-range numeric coordinates are skipped as spurious values.

    Parameters
    ----------
    path : Path
        Path to the BLN file to parse.

    Returns
    -------
    list[BLNRecord]
        Ordered sequence of coordinate points forming the polygon boundary.

    Raises
    ------
    GeometryError
        If the file contains fewer than 3 valid coordinate pairs, which is
        insufficient to form a polygon.
    """
    points: list[BLNRecord] = []
    for lineno, line in enumerate(_iter_lines(path), start=1):
        # BLN sometimes has header lines with counts; ignore if they don't parse.
        line = line.replace("\t", ",")
        parts = [p for p in line.split(",") if p]
        if len(parts) < 2:
            continue
        try:
            x = float(parts[0])
            y = float(parts[1])
        except ValueError:
            # Skip non-numeric lines silently (these are typically headers)
            continue
        # Validate longitude/latitude ranges; skip out-of-bounds points
        if not (-180.0 <= x <= 180.0) or not (-90.0 <= y <= 90.0):
            logger.debug(
                "Skipping out-of-bounds coordinate at line %d in %s: x=%s, y=%s",
                lineno,
                path,
                x,
                y,
            )
            continue
        points.append(BLNRecord(x, y))
    if len(points) < 3:
        raise GeometryError(
            "Polygon requires at least 3 coordinate points, found "
            f"{len(points)} in {path}"
        )
    return points


def convert_file(input_path: Path, output_path: Path) -> None:
    """Convert a single geospatial file to the specified format.

    Determines the input and output formats from file extensions and uses the
    appropriate format handlers for conversion. Supports any readable format
    registered in the format registry as input, and any writable format as
    output. BLN is read-only (input only) and SVG is write-only (output only).

    Parameters
    ----------
    input_path : Path
        Path to the source file to convert (any supported readable format).
    output_path : Path
        Path where the converted file should be saved. The file extension
        determines the output format (e.g., .geojson, .shp, .svg).

    Raises
    ------
    FileParsingError
        If the input file cannot be parsed due to format/content issues.
    FormatNotSupportedError
        If the input or output format is not supported by any registered handler.
    FormatReadOnlyError
        If the output format is read-only and cannot be written to.
    FormatWriteOnlyError
        If the input format is write-only and cannot be read from (e.g., SVG).
    """
    # Lazy imports to avoid circular dependencies with formats -> core
    from .formats import load_any
    from .formats import write_any

    gdf = load_any(input_path)
    ext = output_path.suffix.lower().lstrip(".")
    write_any(gdf, output_path, ext)


def convert_path(
    input_path: Path, output_format: str, output_dir: Path | None = None
) -> None:
    """Convert geospatial file(s) with automatic output path generation.

    Batch conversion utility that handles both single files and directories.
    Automatically generates output paths by replacing the extension
    with the specified target format extension.

    Parameters
    ----------
    input_path : Path
        Source path - can be a single file or a directory containing files.
    output_format : str
        Target format extension (without dot), e.g., 'geojson', 'shp', 'svg'.
    output_dir : Path, optional
        Directory where converted files should be saved. If None, uses the
        same directory as the source file(s).

    Raises
    ------
    FileNotFoundError
        If the source path does not exist.

    Notes
    -----
    - For single files: replaces extension with target format
    - For directories: processes all supported readable formats recursively
      (skips write-only inputs like SVG)
    - Creates output directory if it doesn't exist
    - Preserves relative directory structure for batch processing
    """
    if input_path.is_file():
        # Single file conversion
        target_dir = output_dir if output_dir else input_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        output_path = target_dir / input_path.with_suffix(f".{output_format}").name
        convert_file(input_path, output_path)

    elif input_path.is_dir():
        # Directory batch conversion
        target_dir = output_dir if output_dir else input_path

        from .exceptions import FormatNotSupportedError
        from .formats import detect_format

        for file in input_path.glob("**/*"):
            if not file.is_file():
                continue
            # Skip unsupported formats and write-only inputs (e.g., SVG)
            try:
                handler = detect_format(file)
                if not handler.reader:
                    continue
            except FormatNotSupportedError:
                continue

            rel_path = file.relative_to(input_path)
            output_file = target_dir / rel_path.with_suffix(f".{output_format}")
            output_file.parent.mkdir(parents=True, exist_ok=True)
            convert_file(file, output_file)
    else:
        raise FileNotFoundError(f"Source path does not exist: {input_path}")


# --- Simple user-facing aliases ---------------------------------------------

def convert(input_path: Path, output_path: Path) -> None:
    """Convert a single file. Alias of convert_file for convenience."""
    convert_file(input_path, output_path)


def convert_dir(
    input_path: Path, output_format: str, output_dir: Path | None = None
) -> None:
    """Convert files in a directory (recursive). Alias of convert_path."""
    convert_path(input_path, output_format, output_dir)


def read_bln(path: Path) -> list[BLNRecord]:
    """Parse a BLN file. Alias of parse_bln for convenience."""
    return parse_bln(path)
