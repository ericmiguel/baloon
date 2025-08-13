"""Pytest configuration and shared fixtures for Baloon tests.

This module centralizes all mocks, fixtures, and test utilities to ensure
consistent testing across the entire test suite.
"""

from pathlib import Path
from typing import Any
from unittest.mock import Mock
from unittest.mock import patch

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from baloon.core import BLNRecord
from baloon.exceptions import BaloonError
from baloon.exceptions import FileParsingError
from baloon.exceptions import FormatNotSupportedError
from baloon.exceptions import GeometryError
from baloon.exceptions import InsufficientDataError


# ==============================================================================
# Test Data Fixtures
# ==============================================================================


@pytest.fixture
def valid_bln_content() -> str:
    """Valid BLN file content for testing."""
    return "0,0\n1,0\n1,1\n0,1\n"


@pytest.fixture
def invalid_bln_content() -> str:
    """Invalid BLN file content (insufficient points)."""
    return "0,0\n1,0\n"


@pytest.fixture
def complex_bln_content() -> str:
    """Complex BLN file with multiple lines and mixed content."""
    return """# Header comment
1,0
-122.0,37.0
-122.1,37.1
-122.05,37.15
-122.0,37.1
-122.0,37.0
# End comment
"""


@pytest.fixture
def sample_bln_records() -> list[BLNRecord]:
    """Sample BLN records for testing."""
    return [
        BLNRecord(0.0, 0.0),
        BLNRecord(1.0, 0.0),
        BLNRecord(1.0, 1.0),
        BLNRecord(0.0, 1.0),
    ]


@pytest.fixture
def sample_geodataframe() -> gpd.GeoDataFrame:
    """Sample GeoDataFrame for testing."""
    polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    return gpd.GeoDataFrame(
        {"name": ["test_polygon"], "description": ["Test polygon"]},
        geometry=[polygon],
        crs="EPSG:4326",
    )


@pytest.fixture
def sample_geojson() -> dict[str, Any]:
    """Sample GeoJSON for testing."""
    return {
        "type": "FeatureCollection",
        "name": "test",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]
                    ],
                },
            }
        ],
    }


# ==============================================================================
# File System Fixtures
# ==============================================================================


@pytest.fixture
def bln_file(tmp_path: Path, valid_bln_content: str) -> Path:
    """Create a temporary BLN file with valid content."""
    file_path = tmp_path / "test.bln"
    file_path.write_text(valid_bln_content)
    return file_path


@pytest.fixture
def invalid_bln_file(tmp_path: Path, invalid_bln_content: str) -> Path:
    """Create a temporary BLN file with invalid content."""
    file_path = tmp_path / "invalid.bln"
    file_path.write_text(invalid_bln_content)
    return file_path


@pytest.fixture
def geojson_file(tmp_path: Path, sample_geojson: dict[str, Any]) -> Path:
    """Create a temporary GeoJSON file."""
    import json

    file_path = tmp_path / "test.geojson"
    file_path.write_text(json.dumps(sample_geojson))
    return file_path


@pytest.fixture
def shapefile_directory(tmp_path: Path, sample_geodataframe: gpd.GeoDataFrame) -> Path:
    """Create a temporary Shapefile with all components."""
    file_path = tmp_path / "test.shp"
    sample_geodataframe.to_file(file_path)
    return tmp_path


@pytest.fixture
def test_files_directory(tmp_path: Path) -> Path:
    """Create directory with multiple test files of different formats."""
    # Create BLN file
    bln_path = tmp_path / "polygon.bln"
    bln_path.write_text("0,0\n1,0\n1,1\n0,1\n")

    # Create GeoJSON file
    geojson_path = tmp_path / "polygon.geojson"
    geojson_content = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                },
                "properties": {},
            }
        ],
    }
    import json

    geojson_path.write_text(json.dumps(geojson_content))

    # Create unsupported file
    unsupported_path = tmp_path / "data.xyz"
    unsupported_path.write_text("unsupported format")

    return tmp_path


# ==============================================================================
# Mock Fixtures
# ==============================================================================


@pytest.fixture
def mock_geopandas():
    """Mock GeoPandas operations."""
    with patch("baloon.formats.gpd") as mock_gpd:
        mock_gdf = Mock(spec=gpd.GeoDataFrame)
        mock_gdf.to_file = Mock()
        mock_gdf.to_json = Mock(return_value='{"type":"FeatureCollection"}')
        mock_gpd.read_file = Mock(return_value=mock_gdf)
        mock_gpd.GeoDataFrame = Mock(return_value=mock_gdf)
        yield mock_gpd


@pytest.fixture
def mock_fiona():
    """Mock Fiona operations for GDAL integration."""
    # Create mock module
    fiona_mock = Mock()
    fiona_mock.env = Mock()
    fiona_mock.env.get_gdal_version_num = Mock(return_value=3090200)  # GDAL 3.9.2
    fiona_mock.supported_drivers = {
        "ESRI Shapefile": "rw",
        "GeoJSON": "rw",
        "GPKG": "rw",
        "KML": "rw",
        "CSV": "rw",
    }

    # Patch the import
    with patch.dict("sys.modules", {"fiona": fiona_mock}):
        yield fiona_mock


@pytest.fixture
def mock_fastkml():
    """Mock FastKML operations."""
    with (
        patch("baloon.formats.kml") as mock_kml,
        patch("baloon.formats.features") as mock_features,
        patch("baloon.formats.geometry") as mock_geometry,
    ):
        # Mock KML structure
        mock_doc = Mock()
        mock_placemark = Mock()
        mock_placemark.name = "Test Placemark"
        mock_placemark.description = "Test Description"
        mock_placemark.geometry = Mock()
        mock_doc.features = [mock_placemark]

        mock_kml_obj = Mock()
        mock_kml_obj.features = [mock_doc]

        mock_kml.KML = Mock(return_value=mock_kml_obj)
        mock_kml.KML.from_string = Mock(return_value=mock_kml_obj)

        yield {
            "kml": mock_kml,
            "features": mock_features,
            "geometry": mock_geometry,
            "kml_obj": mock_kml_obj,
        }


# ==============================================================================
# Error Testing Fixtures
# ==============================================================================


@pytest.fixture
def mock_file_read_error():
    """Mock file reading errors."""
    with patch("pathlib.Path.read_text", side_effect=OSError("Permission denied")):
        yield


@pytest.fixture
def mock_geometry_error():
    """Mock geometry processing errors."""
    with patch("shapely.geometry.Polygon", side_effect=Exception("Invalid geometry")):
        yield


# ==============================================================================
# CLI Testing Fixtures
# ==============================================================================


@pytest.fixture
def cli_runner():
    """Typer CLI test runner."""
    from typer.testing import CliRunner

    return CliRunner()


@pytest.fixture
def mock_console():
    """Mock Rich console for CLI testing."""
    with patch("baloon.cli.console") as mock_console:
        mock_console.print = Mock()
        yield mock_console


# ==============================================================================
# Exception Testing Fixtures
# ==============================================================================


@pytest.fixture
def all_exceptions() -> list[type[BaloonError]]:
    """List of all Baloon exception types for comprehensive testing."""
    return [
        BaloonError,
        FormatNotSupportedError,
        FileParsingError,
        GeometryError,
        InsufficientDataError,
    ]


# ==============================================================================
# Utility Functions
# ==============================================================================


def create_test_file(tmp_path: Path, filename: str, content: str) -> Path:
    """Utility function to create test files."""
    file_path = tmp_path / filename
    file_path.write_text(content)
    return file_path


def assert_file_contains(file_path: Path, expected_content: str) -> None:
    """Utility function to assert file contains expected content."""
    assert file_path.exists(), f"File {file_path} does not exist"
    content = file_path.read_text()
    assert expected_content in content, (
        f"Expected '{expected_content}' not found in {file_path}"
    )


def assert_valid_geojson(file_path: Path) -> None:
    """Utility function to assert file is valid GeoJSON."""
    import json

    assert file_path.exists(), f"GeoJSON file {file_path} does not exist"
    content = json.loads(file_path.read_text())
    assert content["type"] == "FeatureCollection"
    assert "features" in content
