"""Core geospatial data processing functionality for Baloon.

This module provides the fundamental data structures and algorithms for parsing
BLN polygon files and converting them to standard geospatial formats.

Classes
-------
BLNRecord
    Represents a single coordinate point from a BLN file.
BLNParseError
    Exception raised when BLN file parsing fails.

Functions
---------
parse_bln
    Parse a BLN polygon file into coordinate records.
convert_file
    Convert a single BLN file to target format(s).
convert_path
    Convert BLN file(s) from a path (file or directory).
discover_bln
    Discover BLN files matching a pattern in a directory tree.

Notes
-----
BLN (Golden Software) files contain polygon boundary data as coordinate pairs,
typically used in geological and mining applications.
"""

import logging
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

try:  # geopandas runtime dependency
    import geopandas as gpd
except Exception:  # pragma: no cover
    gpd = None  # type: ignore

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


class BLNParseError(RuntimeError):
    """Exception raised when BLN file parsing encounters unrecoverable errors.

    This exception is raised when:
    - File contains insufficient coordinate points (< 3 for polygon)
    - File format is corrupted beyond recovery
    - Required coordinate data is missing

    Attributes
    ----------
    message : str
        Human-readable error description.

    Examples
    --------
    >>> try:
    ...     parse_bln(Path("invalid.bln"))
    ... except BLNParseError as e:
    ...     print(f"Parse failed: {e}")
    """

    pass


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
    BLNParseError
        If the file contains fewer than 3 valid coordinate pairs, which is
        insufficient to form a polygon.

    Notes
    -----
    - Lines that cannot be parsed as coordinates are silently skipped
    - Header lines with metadata are automatically ignored
    - Both comma and tab separators are supported
    - Minimum of 3 coordinate pairs required for valid polygon

    Examples
    --------
    >>> from pathlib import Path
    >>> # Create a simple square BLN file
    >>> bln_content = "0,0\\n1,0\\n1,1\\n0,1\\n"
    >>> bln_file = Path("square.bln")
    >>> bln_file.write_text(bln_content)
    >>> records = parse_bln(bln_file)
    >>> len(records)
    4
    >>> records[0].x, records[0].y
    (0.0, 0.0)
    """
    points: list[BLNRecord] = []
    for line in _iter_lines(path):
        # BLN sometimes has header lines with counts; ignore if they don't parse.
        line = line.replace("\t", ",")
        parts = [p for p in line.split(",") if p]
        if len(parts) < 2:
            continue
        try:
            x = float(parts[0])
            y = float(parts[1])
        except ValueError:
            logger.debug("Skipping non-numeric line %s", line)
            continue
        points.append(BLNRecord(x, y))
    if len(points) < 3:
        raise BLNParseError(f"Not enough coordinate lines in {path} (found {len(points)})")
    return points


def convert_file(bln_path: Path, output_path: Path) -> None:
    """Convert a single BLN file to the specified format.

    Determines the output format from the file extension and uses the
    appropriate format handler for conversion.

    Parameters
    ----------
    bln_path : Path
        Path to the source BLN file to convert.
    output_path : Path
        Path where the converted file should be saved. The file extension
        determines the output format (e.g., .geojson, .shp, .svg).

    Raises
    ------
    BLNParseError
        If the BLN file cannot be parsed or has insufficient coordinate data.
    RuntimeError
        If the output format is not supported by any registered format handler.

    Notes
    -----
    - Output format is auto-detected from the file extension
    - Supports all formats registered in the format registry
    - Intermediate conversion through Shapely Polygon for geometry operations

    Examples
    --------
    >>> from pathlib import Path
    >>> bln_file = Path("boundary.bln")
    >>> geojson_file = Path("boundary.geojson")
    >>> convert_file(bln_file, geojson_file)  # Converts to GeoJSON

    >>> svg_file = Path("boundary.svg")
    >>> convert_file(bln_file, svg_file)     # Converts to SVG
    """
    from .formats import write_any

    points = parse_bln(bln_path)
    coords = [(pt.x, pt.y) for pt in points]

    from shapely import Polygon

    geom = Polygon(coords)

    # Convert to GeoDataFrame for format system
    if gpd is None:  # pragma: no cover
        raise RuntimeError("GeoPandas required for format conversion")
    gdf = gpd.GeoDataFrame(index=[0], geometry=[geom], crs="EPSG:4326")

    ext = output_path.suffix.lower().lstrip(".")
    write_any(gdf, output_path, ext)


def convert_path(bln_path: Path, output_format: str, output_dir: Path | None = None) -> None:
    """Convert BLN files with automatic output path generation.

    Batch conversion utility that handles both single files and directories.
    Automatically generates output paths by replacing the .bln extension
    with the specified format extension.

    Parameters
    ----------
    bln_path : Path
        Source path - can be a single BLN file or directory containing BLN files.
    output_format : str
        Target format extension (without dot), e.g., 'geojson', 'shp', 'svg'.
    output_dir : Path, optional
        Directory where converted files should be saved. If None, uses the
        same directory as the source file(s).

    Raises
    ------
    BLNParseError
        If any BLN file cannot be parsed or has insufficient coordinate data.
    RuntimeError
        If the specified output format is not supported.
    FileNotFoundError
        If the source path does not exist.

    Notes
    -----
    - For single files: replaces .bln extension with target format
    - For directories: processes all .bln files recursively
    - Creates output directory if it doesn't exist
    - Preserves relative directory structure for batch processing

    Examples
    --------
    >>> from pathlib import Path
    >>> # Convert single file to GeoJSON in same directory
    >>> convert_path(Path("data.bln"), "geojson")

    >>> # Convert all BLN files in directory to SVG format
    >>> source_dir = Path("boundaries/")
    >>> output_dir = Path("svg_output/")
    >>> convert_path(source_dir, "svg", output_dir)
    """
    if bln_path.is_file():
        # Single file conversion
        target_dir = output_dir if output_dir else bln_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        output_path = target_dir / bln_path.with_suffix(f".{output_format}").name
        convert_file(bln_path, output_path)

    elif bln_path.is_dir():
        # Directory batch conversion
        target_dir = output_dir if output_dir else bln_path

        for bln_file in bln_path.glob("**/*.bln"):
            rel_path = bln_file.relative_to(bln_path)
            output_file = target_dir / rel_path.with_suffix(f".{output_format}")

            output_file.parent.mkdir(parents=True, exist_ok=True)
            convert_file(bln_file, output_file)
    else:
        raise FileNotFoundError(f"Source path does not exist: {bln_path}")


# Legacy function for compatibility with formats module
def _to_polygon(records: Sequence[BLNRecord]) -> BaseGeometry:
    """Convert BLN records to a Shapely Polygon.

    Helper function for the format system.
    """
    coords = [(r.x, r.y) for r in records]
    if coords[0] != coords[-1]:
        coords.append(coords[0])  # type: ignore[arg-type]
    poly = Polygon(coords)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly
