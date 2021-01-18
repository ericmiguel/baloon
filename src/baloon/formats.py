"""Format registry for Baloon.

Provides pluggable readers and writers for geospatial vector formats:
 - BLN (Golden Software) - read only
 - Shapefile - read/write via GeoPandas
 - GeoJSON - read/write via GeoPandas
 - GeoPackage - read/write via GeoPandas
 - KML - read/write via fastkml
 - SVG - write only, 2D projection without CRS transform

Additional formats can be registered via :func:`register_format`.
"""

from collections.abc import Callable
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any
from typing import Final
from typing import Iterable
from typing import Protocol
from typing import TypeGuard
from typing import Union
from typing import cast

from fastkml import features
from fastkml import geometry
from fastkml import kml
import geopandas as gpd
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

from .core import BLNRecord
from .core import parse_bln
from .exceptions import FileParsingError
from .exceptions import FormatNotSupportedError
from .exceptions import FormatReadOnlyError
from .exceptions import FormatWriteOnlyError
from .exceptions import GeometryError
from .exceptions import InsufficientDataError


class HasFeatures(Protocol):
    """Protocol for KML containers that expose an iterable 'features' attribute."""

    features: Iterable[Any]


# Define a public alias for fastkml geometry union
KmlGeom = Union[
    geometry.Point, geometry.LineString, geometry.Polygon, geometry.MultiGeometry
]


@dataclass(slots=True)
class KMLGeometryChoice:
    """Helper to select the first present fastkml geometry among alternatives."""

    point: geometry.Point | None = None
    linestring: geometry.LineString | None = None
    polygon: geometry.Polygon | None = None
    multigeometry: geometry.MultiGeometry | None = None

    @property
    def value(self) -> KmlGeom:
        """Return the first available fastkml geometry.

        Raises
        ------
        GeometryError
            If none of the geometry options are provided.
        """
        geom: KmlGeom | None = None
        for v in (self.point, self.linestring, self.polygon, self.multigeometry):
            if v is not None:
                geom = v
                break
        if geom is None:
            raise GeometryError("No valid KML geometry found.")
        return geom


def _to_polygon(records: list[BLNRecord]) -> Polygon:
    """Convert BLN records to a Shapely Polygon.

    Parameters
    ----------
    records : list
        List of BLNRecord objects with x and y coordinates.

    Returns
    -------
    Polygon
        Shapely polygon created from the coordinate records.

    Raises
    ------
    InsufficientDataError
        If fewer than 3 coordinate pairs are provided.
    """
    if len(records) < 3:
        raise InsufficientDataError(
            "Cannot create polygon from coordinate records",
            required=3,
            found=len(records),
        )

    coordinates = [(record.x, record.y) for record in records]
    return Polygon(coordinates)


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FormatHandler:
    """Handler for a specific geospatial file format.

    Defines the interface for reading and writing geospatial data in a
    particular format. Each handler specifies supported file extensions
    and provides optional reader/writer functions.

    Parameters
    ----------
    name : str
        Human-readable format name (e.g., 'GeoJSON', 'Shapefile').
    extensions : list[str]
        File extensions supported by this format (without dots).
    reader : callable or None
        Function to read files in this format, signature: (Path) -> GeoDataFrame.
    writer : callable or None
        Function to write files in this format, signature: (GeoDataFrame, Path) -> None.
    description : str, default ""
        Description of the format and its capabilities.
    """

    name: str
    extensions: list[str]
    reader: Callable[[Path], gpd.GeoDataFrame] | None = None
    writer: Callable[[gpd.GeoDataFrame, Path], None] | None = None
    description: str = ""


_REGISTRY: Final[dict[str, FormatHandler]] = {}


def register_format(handler: FormatHandler) -> None:
    """Register a new format handler in the global registry.

    Parameters
    ----------
    handler : FormatHandler
        Format handler specification with name, extensions,
        and optional reader/writer functions.

    Notes
    -----
    Each extension will be mapped to the same handler instance.
    Extension matching is case-insensitive.
    Later registrations override earlier ones for same extensions.
    """
    for ext in handler.extensions:
        _REGISTRY[ext.lower()] = handler


def list_formats() -> list[FormatHandler]:
    """List all registered format handlers.

    Returns
    -------
    list[FormatHandler]
        Unique format handlers sorted alphabetically by name.

    Notes
    -----
    Since multiple extensions can map to the same handler,
    this function deduplicates the results.
    """
    seen: dict[str, FormatHandler] = {}
    for h in _REGISTRY.values():
        seen[h.name] = h
    return sorted(seen.values(), key=lambda h: h.name)


def detect_format(path: Path) -> FormatHandler:
    """Detect the format handler for a given file path.

    Parameters
    ----------
    path : Path
        File path with extension to analyze.

    Returns
    -------
    FormatHandler
        The format handler for this file type.

    Raises
    ------
    FormatNotSupportedError
        If the file extension is not supported by any registered handler.
    """
    ext = path.suffix.lower().lstrip(".")
    if ext not in _REGISTRY:
        raise FormatNotSupportedError(ext, str(path))
    return _REGISTRY[ext]


def load_any(path: Path) -> gpd.GeoDataFrame:
    """Load geospatial data from any supported format.

    Parameters
    ----------
    path : Path
        Path to the geospatial file to load.

    Returns
    -------
    gpd.GeoDataFrame
        Loaded geospatial data with geometry and optional attributes.

    Raises
    ------
    FormatNotSupportedError
        If the file format is not supported by any registered handler.
    FormatWriteOnlyError
        If the file format is write-only and cannot be read.
    FileParsingError
        If the file cannot be parsed due to format or content issues.
    """
    handler = detect_format(path)
    if not handler.reader:
        raise FormatWriteOnlyError(handler.name, str(path))
    reader = cast(Callable[[Path], gpd.GeoDataFrame], handler.reader)
    return reader(path)


def write_any(gdf: gpd.GeoDataFrame, out_path: Path, target_ext: str) -> None:
    """Write geospatial data to any supported format.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        Geospatial data to write.
    out_path : Path
        Output file path where data should be saved.
    target_ext : str
        File extension (without dot) specifying the output format.

    Raises
    ------
    FormatNotSupportedError
        If the target format is not supported by any registered handler.
    FormatReadOnlyError
        If the target format is read-only and cannot be written to.
    """
    # Create parent directory if it doesn't exist
    out_path.parent.mkdir(parents=True, exist_ok=True)

    handler = _REGISTRY.get(target_ext.lower())
    if not handler or not handler.writer:
        raise FormatReadOnlyError(target_ext, str(out_path))
    writer = cast(Callable[[gpd.GeoDataFrame, Path], None], handler.writer)
    writer(gdf, out_path)


# --- Built-in Format Handlers --------------------


def _read_bln(path: Path) -> gpd.GeoDataFrame:
    """Read BLN polygon file into GeoDataFrame.

    Parameters
    ----------
    path : Path
        Path to the BLN file to read.

    Returns
    -------
    gpd.GeoDataFrame
        Single-feature GeoDataFrame containing the polygon geometry
        with WGS84 CRS (EPSG:4326).
    """
    records = parse_bln(path)
    poly = _to_polygon(records)  # type: ignore[arg-type]
    return gpd.GeoDataFrame(index=[0], geometry=[poly], crs="EPSG:4326")


_DRIVER_MAP: Final[dict[str, str]] = {
    "shp": "ESRI Shapefile",
    "geojson": "GeoJSON",
}


def _write_vector(gdf: gpd.GeoDataFrame, out_path: Path) -> None:
    """Write GeoDataFrame to standard vector format.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        Geospatial data to write.
    out_path : Path
        Output file path with .shp or .geojson extension.

    Raises
    ------
    ValueError
        If the file extension is not supported.
    """
    ext = out_path.suffix.lower().lstrip(".")
    driver = _DRIVER_MAP.get(ext)
    if not driver:
        raise FormatNotSupportedError(ext, str(out_path))
    gdf.to_file(out_path, driver=driver)


def _read_vector(path: Path) -> gpd.GeoDataFrame:
    """Read standard vector file into GeoDataFrame.

    Parameters
    ----------
    path : Path
        Path to the vector file to read.

    Returns
    -------
    gpd.GeoDataFrame
        Loaded geospatial data.
    """
    return gpd.read_file(path)


def _read_geopackage(path: Path) -> gpd.GeoDataFrame:
    """Read GeoPackage file into GeoDataFrame.

    Parameters
    ----------
    path : Path
        Path to the GeoPackage file.

    Returns
    -------
    gpd.GeoDataFrame
        Loaded geospatial data.
    """
    return gpd.read_file(path, driver="GPKG")


def _write_geopackage(gdf: gpd.GeoDataFrame, path: Path) -> None:
    """Write GeoDataFrame to GeoPackage file.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        The GeoDataFrame to write.
    path : Path
        Path where the GeoPackage file should be created.
    """
    gdf.to_file(path, driver="GPKG")


def is_placemark_with_geometry(item: object) -> TypeGuard[features.Placemark]:
    """Type guard for a Placemark that also contains a geometry."""
    if isinstance(item, features.Placemark):
        return bool(item.kml_geometry)
    return False


def _as_shapely(obj: object) -> BaseGeometry:
    """Return a Shapely geometry from a fastkml/pygeoif geometry-like object."""
    return cast(BaseGeometry, obj.geometry if hasattr(obj, "geometry") else obj)


def _read_kml(path: Path) -> gpd.GeoDataFrame:
    """Read KML file into GeoDataFrame.

    Parameters
    ----------
    path : Path
        Path to the KML file to read.

    Returns
    -------
    gpd.GeoDataFrame
        Loaded geospatial data from KML.

    Raises
    ------
    FileParsingError
        If KML reading fails due to malformed content or parsing errors.
    InsufficientDataError
        If the KML file contains no valid geometries.
    """
    # Always use manual KML parsing to avoid GDAL dependency issues
    geometries: list[BaseGeometry] = []
    names: list[str] = []
    descriptions: list[str] = []

    try:
        with path.open("r", encoding="utf-8") as f:
            content = f.read()
            # Remove XML declaration if present (fastkml doesn't like it)
            if content.startswith("<?xml"):
                content = content.split(">", 1)[1] if ">" in content else content
            k = kml.KML()
            k.from_string(content)
    except Exception as e:
        raise FileParsingError(
            message=f"Failed to parse KML file: {e}", path=str(path)
        ) from e

    # Extract geometries from all placemarks
    def extract_placemarks(container: HasFeatures) -> None:
        """Recursively extract placemarks from KML containers."""
        if not hasattr(container, "features"):
            return
        for item in container.features:
            if is_placemark_with_geometry(item):
                shapely_geom = _as_shapely(item.kml_geometry)
                geometries.append(shapely_geom)
                name = item.name or f"Feature_{len(geometries)}"
                names.append(name)
                descriptions.append(item.description or "")
            elif hasattr(item, "features"):
                extract_placemarks(cast(HasFeatures, item))

    extract_placemarks(cast(HasFeatures, k))

    if not geometries:
        raise InsufficientDataError(
            message=f"No valid geometries found in KML file '{path}'",
            required=1,
            found=0,
            path=str(path),
        )

    # Create GeoDataFrame with extracted data
    data = {"name": names, "description": descriptions}
    return gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:4326")


def _write_kml(gdf: gpd.GeoDataFrame, out_path: Path) -> None:
    """Write GeoDataFrame to KML format.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        The GeoDataFrame to write.
    out_path : Path
        Path where the KML file should be created.
    """
    # Create KML document structure
    k = kml.KML()
    # Use Document (it exists in the API despite linter warnings)
    doc = kml.Document(name=out_path.stem, description="Generated by Baloon")  # type: ignore
    k.append(doc)

    # Convert each row to a KML Placemark
    for idx, row in gdf.iterrows():
        if row.geometry is None or row.geometry.is_empty:
            continue

        # Create placemark name (use index if no name column)
        placemark_name = f"Feature_{idx}"
        if "name" in gdf.columns and row["name"]:
            placemark_name = str(row["name"])
        elif "Name" in gdf.columns and row["Name"]:
            placemark_name = str(row["Name"])

        # Create description from other attributes
        description_parts: list[str] = []
        for col in gdf.columns:
            if col not in ["geometry", "name", "Name"] and row[col] is not None:
                description_parts.append(f"{col}: {row[col]}")
        description = (
            "; ".join(description_parts) if description_parts else "No description"
        )

        # Convert Shapely geometry to fastkml geometry
        try:
            # Create appropriate fastkml geometry based on Shapely geometry type
            shapely_geom = row.geometry
            geom_type = shapely_geom.geom_type

            geom_type_map: dict[str, Callable[[Any], KMLGeometryChoice]] = {
                "Point": lambda g: KMLGeometryChoice(point=geometry.Point(geometry=g)),
                "LineString": lambda g: KMLGeometryChoice(
                    linestring=geometry.LineString(geometry=g)
                ),
                "Polygon": lambda g: KMLGeometryChoice(
                    polygon=geometry.Polygon(geometry=g)
                ),
                "MultiPoint": lambda g: KMLGeometryChoice(
                    multigeometry=geometry.MultiGeometry(geometry=g)
                ),
                "MultiLineString": lambda g: KMLGeometryChoice(
                    multigeometry=geometry.MultiGeometry(geometry=g)
                ),
                "MultiPolygon": lambda g: KMLGeometryChoice(
                    multigeometry=geometry.MultiGeometry(geometry=g)
                ),
            }

            if geom_type not in geom_type_map:
                raise GeometryError(
                    f"Unsupported geometry type '{geom_type}' for feature {idx}"
                )

            kml_geom = geom_type_map[geom_type](shapely_geom).value

            # Create placemark with geometry
            pm = features.Placemark(
                name=placemark_name, description=description, kml_geometry=kml_geom
            )
            doc.append(pm)
        except Exception as e:
            raise GeometryError(
                f"Failed to convert geometry for feature {idx}: {e}"
            ) from e

    # Write KML to file
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + k.to_string(
        prettyprint=True
    )
    out_path.write_text(xml_content, encoding="utf-8")


def _write_svg(gdf: gpd.GeoDataFrame, out_path: Path) -> None:
    """Write GeoDataFrame to SVG format.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        The GeoDataFrame to write.
    out_path : Path
        Path where the SVG file should be created.
    """
    minx, miny, maxx, maxy = gdf.total_bounds
    width = max(1.0, maxx - minx)
    height = max(1.0, maxy - miny)
    svg_width = 800
    scale = svg_width / width if width else 1
    svg_height = height * scale

    def _poly_to_path(poly: Polygon) -> str:
        coords = list(poly.exterior.coords)
        d = (
            "M "
            + " L ".join(
                f"{(x - minx) * scale:.2f},{(maxy - y) * scale:.2f}" for x, y in coords
            )
            + " Z"
        )
        return f"<path d=\"{d}\" fill='none' stroke='black' stroke-width='1' />"

    paths: list[str] = []
    for geom in gdf.geometry:
        if geom.is_empty:
            continue
        if geom.geom_type == "Polygon":
            paths.append(_poly_to_path(geom))  # type: ignore[arg-type]
        elif geom.geom_type == "MultiPolygon":
            for pg in geom.geoms:  # type: ignore[attr-defined]
                paths.append(_poly_to_path(pg))
        else:
            raise GeometryError(
                f"SVG export only supports Polygon and MultiPolygon geometries, "
                f"found: {geom.geom_type}"
            )

    svg = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{svg_width}' "
        f"height='{svg_height}' viewBox='0 0 {svg_width} {svg_height}'>",
        *paths,
        "</svg>",
    ]
    out_path.write_text("\n".join(svg), encoding="utf-8")


# --- Format Registration --------------------

register_format(
    FormatHandler(
        name="BLN",
        extensions=["bln"],
        reader=_read_bln,
        writer=None,
        description="Golden Software BLN polygon file (read-only)",
    )
)

register_format(
    FormatHandler(
        name="Shapefile",
        extensions=["shp"],
        reader=_read_vector,
        writer=_write_vector,
        description="ESRI Shapefile with .shp, .shx, .dbf components",
    )
)

register_format(
    FormatHandler(
        name="GeoJSON",
        extensions=["geojson", "json"],
        reader=_read_vector,
        writer=_write_vector,
        description="RFC 7946 GeoJSON feature collection",
    )
)

register_format(
    FormatHandler(
        name="SVG",
        extensions=["svg"],
        reader=None,
        writer=_write_svg,
        description="Scalable Vector Graphics 2D projection (write-only)",
    )
)

register_format(
    FormatHandler(
        name="GeoPackage",
        extensions=["gpkg"],
        reader=_read_geopackage,
        writer=_write_geopackage,
        description="OGC GeoPackage (SQLite-based multi-layer format)",
    )
)

register_format(
    FormatHandler(
        name="KML",
        extensions=["kml", "kmz"],
        reader=_read_kml,
        writer=_write_kml,
        description="Keyhole Markup Language (Google Earth format)",
    )
)
