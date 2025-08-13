"""Format registry for Baloon.

Provides pluggable readers and writers for geospatial vector formats:
 - BLN (Golden Software) (read)
 - Shapefile (read/write via GeoPandas)
 - GeoJSON (read/write via GeoPandas)
 - GeoPackage (read/write via GeoPandas)
 - KML (write via fastkml, read via GeoPandas)
 - SVG (write only) simple 2D projection (no CRS transform)

Additional formats can register via :func:`register_format`.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Polygon

from .core import _to_polygon, parse_bln  # type: ignore

# Optional KML dependencies
try:
    from fastkml import kml, features
    import pygeoif
    KML_AVAILABLE = True
except ImportError:
    KML_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FormatHandler:
    """Handler for a specific geospatial file format.

    Defines the interface for reading and writing geospatial data in a
    particular format. Each handler specifies supported file extensions
    and provides optional reader/writer functions.

    Attributes
    ----------
    name : str
        Human-readable format name (e.g., 'GeoJSON', 'Shapefile').
    extensions : list[str]
        File extensions supported by this format (without dots).
    reader : Callable[[Path], gpd.GeoDataFrame] or None
        Function to read files in this format, or None if read-only.
    writer : Callable[[gpd.GeoDataFrame, Path], None] or None
        Function to write files in this format, or None if write-only.
    description : str, optional
        Detailed description of the format and its capabilities.

    Examples
    --------
    >>> def read_custom(path):
    ...     return gpd.read_file(path)
    >>> def write_custom(gdf, path):
    ...     gdf.to_file(path, driver='GPKG')
    >>> handler = FormatHandler(
    ...     name='GeoPackage',
    ...     extensions=['gpkg'],
    ...     reader=read_custom,
    ...     writer=write_custom,
    ...     description='SQLite-based geospatial format'
    ... )
    """

    name: str
    extensions: list[str]
    reader: Callable[[Path], gpd.GeoDataFrame] | None = None
    writer: Callable[[gpd.GeoDataFrame, Path], None] | None = None
    description: str = ""


_REGISTRY: dict[str, FormatHandler] = {}


def register_format(handler: FormatHandler) -> None:
    """Register a new format handler in the global registry.

    Adds support for a new geospatial file format by registering
    reader/writer functions for the specified file extensions.

    Parameters
    ----------
    handler : FormatHandler
        Complete format handler specification with name, extensions,
        and optional reader/writer functions.

    Notes
    -----
    - Each extension will be mapped to the same handler instance
    - Extension matching is case-insensitive
    - Later registrations override earlier ones for same extensions

    Examples
    --------
    >>> def read_kml(path):
    ...     return gpd.read_file(path, driver='KML')
    >>> kml_handler = FormatHandler(
    ...     name='KML',
    ...     extensions=['kml'],
    ...     reader=read_kml,
    ...     description='Keyhole Markup Language'
    ... )
    >>> register_format(kml_handler)
    """
    for ext in handler.extensions:
        _REGISTRY[ext.lower()] = handler


def list_formats() -> list[FormatHandler]:
    """List all registered format handlers.

    Returns unique format handlers sorted alphabetically by name.
    Since multiple extensions can map to the same handler, this
    function deduplicates the results.

    Returns
    -------
    list[FormatHandler]
        All unique format handlers, sorted by name.

    Examples
    --------
    >>> formats = list_formats()
    >>> for fmt in formats:
    ...     print(f"{fmt.name}: {', '.join(fmt.extensions)}")
    BLN: bln
    GeoJSON: geojson
    SVG: svg
    Shapefile: shp
    """
    seen = {}
    for h in _REGISTRY.values():
        seen[h.name] = h
    return sorted(seen.values(), key=lambda h: h.name)


def detect_format(path: Path) -> FormatHandler:
    """Detect the format handler for a given file path.

    Uses the file extension to lookup the appropriate format handler
    from the registry.

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
    ValueError
        If the file extension is not supported by any registered handler.

    Examples
    --------
    >>> from pathlib import Path
    >>> handler = detect_format(Path('data.geojson'))
    >>> handler.name
    'GeoJSON'
    """
    ext = path.suffix.lower().lstrip(".")
    if ext not in _REGISTRY:
        raise ValueError(f"Unsupported / unknown format for '{path.name}'.")
    return _REGISTRY[ext]


def load_any(path: Path) -> gpd.GeoDataFrame:
    """Load geospatial data from any supported format.

    Automatically detects the file format and uses the appropriate
    reader function to load the data into a GeoDataFrame.

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
    ValueError
        If the file format is not supported or is write-only.

    Examples
    --------
    >>> from pathlib import Path
    >>> gdf = load_any(Path('boundaries.geojson'))
    >>> print(f"Loaded {len(gdf)} features")
    """
    handler = detect_format(path)
    if not handler.reader:
        raise ValueError(f"Format '{handler.name}' is write-only.")
    return handler.reader(path)


def write_any(gdf: gpd.GeoDataFrame, out_path: Path, target_ext: str) -> None:
    """Write geospatial data to any supported format.

    Uses the specified file extension to determine the output format
    and applies the appropriate writer function.

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
    ValueError
        If the target format is not supported or is read-only.

    Examples
    --------
    >>> import geopandas as gpd
    >>> from pathlib import Path
    >>> gdf = gpd.read_file('input.geojson')
    >>> write_any(gdf, Path('output.shp'), 'shp')
    """
    handler = _REGISTRY.get(target_ext.lower())
    if not handler or not handler.writer:
        raise ValueError(f"No writer for format '{target_ext}'.")
    handler.writer(gdf, out_path)


# --- Built-in Format Handlers ----------------------------------------------------------


def _read_bln(path: Path) -> gpd.GeoDataFrame:
    """Read BLN polygon file into GeoDataFrame.

    Internal reader function that parses BLN coordinate data and
    converts it to a single-polygon GeoDataFrame with WGS84 CRS.

    Parameters
    ----------
    path : Path
        Path to the BLN file to read.

    Returns
    -------
    gpd.GeoDataFrame
        Single-feature GeoDataFrame containing the polygon geometry.
    """
    records = parse_bln(path)
    poly = _to_polygon(records)  # type: ignore[arg-type]
    return gpd.GeoDataFrame(index=[0], geometry=[poly], crs="EPSG:4326")


def _write_vector(gdf: gpd.GeoDataFrame, out_path: Path) -> None:
    """Write GeoDataFrame to standard vector format.

    Internal writer function supporting Shapefile and GeoJSON formats
    via GeoPandas with automatic driver detection.

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
    driver = {"shp": "ESRI Shapefile", "geojson": "GeoJSON"}.get(ext)
    if not driver:
        raise ValueError(f"Unsupported driver for extension '{ext}'.")
    gdf.to_file(out_path, driver=driver)


def _read_vector(path: Path) -> gpd.GeoDataFrame:
    """Read standard vector file into GeoDataFrame.

    Internal reader function that delegates to GeoPandas for
    automatic format detection and loading.

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
    
    Internal reader function for SQLite-based GeoPackage format.
    If multiple layers exist, reads the first layer by default.
    
    Parameters
    ----------
    path : Path
        Path to the GeoPackage (.gpkg) file to read.
        
    Returns
    -------
    gpd.GeoDataFrame
        Loaded geospatial data from the GeoPackage.
        
    Notes
    -----
    - Uses GDAL GPKG driver through GeoPandas
    - For multi-layer packages, only reads the first layer
    - Supports all OGC GeoPackage features including CRS metadata
    """
    return gpd.read_file(path, driver='GPKG')


def _write_geopackage(gdf: gpd.GeoDataFrame, out_path: Path) -> None:
    """Write GeoDataFrame to GeoPackage format.
    
    Internal writer function for SQLite-based GeoPackage files.
    Creates a single layer with the same name as the file stem.
    
    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        Geospatial data to write.
    out_path : Path
        Output GeoPackage (.gpkg) file path.
        
    Notes
    -----
    - Uses GDAL GPKG driver through GeoPandas
    - Creates single layer named after the file
    - Preserves CRS information and attributes
    - Overwrites existing files
    """
    layer_name = out_path.stem
    gdf.to_file(out_path, driver='GPKG', layer=layer_name)


def _read_kml(path: Path) -> gpd.GeoDataFrame:
    """Read KML file into GeoDataFrame.
    
    Internal reader function for Keyhole Markup Language files.
    Uses GeoPandas with fallback to manual parsing if needed.
    
    Parameters
    ----------
    path : Path
        Path to the KML file to read.
        
    Returns
    -------
    gpd.GeoDataFrame
        Loaded geospatial data from KML.
        
    Notes
    -----
    - First attempts GeoPandas reading (requires GDAL KML driver)
    - Falls back to direct KML parsing if GeoPandas fails
    - May not preserve all KML styling information
    """
    try:
        # Try GeoPandas first (works if GDAL has KML support)
        return gpd.read_file(path)
    except Exception:
        # Fallback: manual KML parsing (if fastkml is available)
        if not KML_AVAILABLE:
            raise RuntimeError("KML support requires fastkml and pygeoif packages")
        
        # Import KML libraries (conditional import)
        from fastkml import kml, features
        
        # Basic KML reading - extract geometries and attributes
        logger.warning("Using basic KML parser - some features may be lost")
        geometries = []
        names = []
        descriptions = []
        
        with path.open('r', encoding='utf-8') as f:
            k = kml.KML()
            k.from_string(f.read())
            
            # Extract geometries from all placemarks  
            # Handle nested structure - documents and folders can contain placemarks
            def extract_placemarks(container):
                """Recursively extract placemarks from KML containers."""
                for item in container.features:
                    if isinstance(item, features.Placemark) and hasattr(item, 'kml_geometry') and item.kml_geometry:
                        # pygeoif geometries are already Shapely-compatible
                        geometries.append(item.kml_geometry)
                        names.append(item.name or f"Feature_{len(geometries)}")
                        descriptions.append(item.description or "")
                    elif hasattr(item, 'features'):
                        # Recurse into folders/documents
                        extract_placemarks(item)
            
            extract_placemarks(k)
        
        if not geometries:
            # Return empty GeoDataFrame with geometry column
            return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
            
        # Create GeoDataFrame with extracted data
        data = {'name': names, 'description': descriptions}
        return gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:4326")


def _write_kml(gdf: gpd.GeoDataFrame, out_path: Path) -> None:
    """Write GeoDataFrame to KML format.
    
    Internal writer function for Keyhole Markup Language files.
    Based on the provided script, modernized for GeoPandas input.
    
    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        Geospatial data to write.
    out_path : Path
        Output KML file path.
        
    Notes
    -----
    - Uses fastkml and pygeoif libraries
    - Creates placemarks for each feature
    - Basic styling and naming support
    - Requires fastkml and pygeoif dependencies
    """
    if not KML_AVAILABLE:
        raise RuntimeError("KML export requires fastkml and pygeoif packages")
    
    # Import KML libraries (conditional import)
    from fastkml import kml, features, geometry
    
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
        if 'name' in gdf.columns and row['name']:
            placemark_name = str(row['name'])
        elif 'Name' in gdf.columns and row['Name']:
            placemark_name = str(row['Name'])
        
        # Create description from other attributes
        description_parts = []
        for col in gdf.columns:
            if col not in ['geometry', 'name', 'Name'] and row[col] is not None:
                description_parts.append(f"{col}: {row[col]}")
        description = "; ".join(description_parts) if description_parts else "No description"
        
        # Convert Shapely geometry to fastkml geometry
        try:
            # Create appropriate fastkml geometry based on Shapely geometry type
            shapely_geom = row.geometry
            geom_type = shapely_geom.geom_type
            
            if geom_type == "Point":
                kml_geom = geometry.Point(geometry=shapely_geom)
            elif geom_type == "LineString":
                kml_geom = geometry.LineString(geometry=shapely_geom)
            elif geom_type == "Polygon":
                kml_geom = geometry.Polygon(geometry=shapely_geom)
            elif geom_type == "MultiPoint":
                kml_geom = geometry.MultiGeometry(geometry=shapely_geom)
            elif geom_type == "MultiLineString":
                kml_geom = geometry.MultiGeometry(geometry=shapely_geom)
            elif geom_type == "MultiPolygon":
                kml_geom = geometry.MultiGeometry(geometry=shapely_geom)
            else:
                logger.warning(f"Unsupported geometry type {geom_type} for feature {idx}")
                continue
            
            # Create placemark with geometry
            pm = features.Placemark(
                name=placemark_name,
                description=description,
                kml_geometry=kml_geom
            )
            doc.append(pm)
        except Exception as e:
            logger.warning(f"Failed to convert geometry for feature {idx}: {e}")
            continue
    
    # Write KML to file
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + k.to_string(prettyprint=True)
    out_path.write_text(xml_content, encoding='utf-8')


def _write_svg(gdf: gpd.GeoDataFrame, out_path: Path) -> None:
    """Write GeoDataFrame geometries to simple SVG format.

    Internal writer function that creates a basic 2D SVG representation
    of polygon geometries. Uses a simple orthographic projection with
    automatic scaling to fit an 800px wide viewport.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        Geospatial data containing Polygon or MultiPolygon geometries.
    out_path : Path
        Output SVG file path.

    Notes
    -----
    - Only supports Polygon and MultiPolygon geometries
    - Uses black stroke with no fill styling
    - Y-axis is flipped for standard SVG coordinate system
    - No CRS transformation is performed
    - Scale is determined by the data bounds
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
            + " L ".join(f"{(x - minx) * scale:.2f},{(maxy - y) * scale:.2f}" for x, y in coords)
            + " Z"
        )
        return f"<path d=\"{d}\" fill='none' stroke='black' stroke-width='1' />"

    paths: list[str] = []
    for geom in gdf.geometry:
        if geom is None:
            continue
        if geom.geom_type == "Polygon":
            paths.append(_poly_to_path(geom))  # type: ignore[arg-type]
        elif geom.geom_type == "MultiPolygon":
            for pg in geom.geoms:  # type: ignore[attr-defined]
                paths.append(_poly_to_path(pg))
        else:
            logger.debug("Skipping unsupported geometry in SVG export: %s", geom.geom_type)

    svg = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{svg_width}' height='{svg_height}' viewBox='0 0 {svg_width} {svg_height}'>",
        *paths,
        "</svg>",
    ]
    out_path.write_text("\n".join(svg), encoding="utf-8")


# --- Format Registration ---------------------------------------------------------------

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

# Register KML format conditionally
if KML_AVAILABLE:
    register_format(
        FormatHandler(
            name="KML",
            extensions=["kml", "kmz"],
            reader=_read_kml,
            writer=_write_kml,
            description="Keyhole Markup Language (Google Earth format)",
        )
    )
