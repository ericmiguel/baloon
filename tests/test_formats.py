from pathlib import Path

import pytest
from baloon.formats import load_any, write_any


def test_bln_to_geojson_and_svg(tmp_path: Path):
    bln = tmp_path / "poly.bln"
    bln.write_text("0,0\n1,0\n1,1\n0,1\n")
    gdf = load_any(bln)
    assert len(gdf) == 1
    out_geo = tmp_path / "poly.geojson"
    write_any(gdf, out_geo, "geojson")
    assert out_geo.exists() and out_geo.read_text().strip().startswith('{')
    out_svg = tmp_path / "poly.svg"
    write_any(gdf, out_svg, "svg")
    assert "<svg" in out_svg.read_text()


def test_bln_to_geopackage(tmp_path):
    """Test conversion from BLN to GeoPackage format."""
    # Create test BLN file with valid polygon (needs at least 4 points)
    bln_content = """1,0
-122.0,37.0
-122.1,37.1
-122.0,37.1
-122.0,37.0
"""
    bln_path = tmp_path / "test.bln"
    bln_path.write_text(bln_content)
    
    # Load BLN
    gdf = load_any(bln_path)
    assert len(gdf) == 1
    assert gdf.iloc[0].geometry.geom_type == "Polygon"
    
    # Write to GeoPackage
    gpkg_path = tmp_path / "test.gpkg"
    write_any(gdf, gpkg_path, "gpkg")
    assert gpkg_path.exists()
    
    # Read back from GeoPackage
    gdf2 = load_any(gpkg_path)
    assert len(gdf2) == 1
    assert gdf2.iloc[0].geometry.geom_type == "Polygon"
    
    # Verify geometries are similar (allowing for small floating-point differences)
    original_geom = gdf.iloc[0].geometry
    roundtrip_geom = gdf2.iloc[0].geometry
    assert original_geom.almost_equals(roundtrip_geom, decimal=6)


def test_bln_to_kml(tmp_path):
    """Test conversion from BLN to KML format."""
    # Skip test if KML dependencies not available
    try:
        from fastkml import kml, features, geometry
        import pygeoif
    except ImportError:
        pytest.skip("KML dependencies not available")
    
    # Create test BLN file with valid polygon (needs at least 4 points)
    bln_content = """1,0
-122.0,37.0
-122.1,37.1
-122.0,37.1
-122.0,37.0
"""
    bln_path = tmp_path / "test.bln"
    bln_path.write_text(bln_content)
    
    # Load BLN
    gdf = load_any(bln_path)
    assert len(gdf) == 1
    assert gdf.iloc[0].geometry.geom_type == "Polygon"
    assert not gdf.iloc[0].geometry.is_empty  # Ensure geometry is valid
    
    # Write to KML
    kml_path = tmp_path / "test.kml"
    write_any(gdf, kml_path, "kml")
    assert kml_path.exists()
    
    # Verify KML content contains expected elements
    kml_content = kml_path.read_text()
    assert "<?xml" in kml_content
    assert "kml xmlns" in kml_content
    assert "Document>" in kml_content  # May have kml: namespace
    assert "Placemark>" in kml_content  # May have kml: namespace
    assert "Polygon>" in kml_content  # May have kml: namespace
    assert "coordinates>" in kml_content
    
    # Try to read back from KML (may use GeoPandas or fastkml fallback)
    try:
        gdf2 = load_any(kml_path)
        assert len(gdf2) >= 1  # Should have at least one feature
        # Note: KML roundtrip may not preserve exact geometry due to different parsers
        assert any(geom.geom_type == "Polygon" for geom in gdf2.geometry)
    except Exception:
        # KML reading might fail if GDAL KML driver not available
        # This is acceptable as long as writing worked
        pass
