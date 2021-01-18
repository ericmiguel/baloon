"""
Tests for baloon.core module.

Tests cover BLN parsing, file conversion, error handling, and edge cases.
"""

from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from baloon.core import BLNRecord
from baloon.core import convert_file
from baloon.core import parse_bln
from baloon.exceptions import GeometryError


class TestBLNRecord:
    """Test BLN record data structure."""

    def test_bln_record_creation(self) -> None:
        """Test BLNRecord creation with valid coordinates."""
        record = BLNRecord(10.5, -20.3)
        assert record.x == 10.5
        assert record.y == -20.3

    def test_bln_record_zero_coordinates(self) -> None:
        """Test BLNRecord with zero coordinates."""
        record = BLNRecord(0.0, 0.0)
        assert record.x == 0.0
        assert record.y == 0.0

    def test_bln_record_negative_coordinates(self) -> None:
        """Test BLNRecord with negative coordinates."""
        record = BLNRecord(-122.4194, 37.7749)
        assert record.x == -122.4194
        assert record.y == 37.7749

    def test_bln_record_equality(self) -> None:
        """Test BLNRecord equality comparison."""
        record1 = BLNRecord(1.0, 2.0)
        record2 = BLNRecord(1.0, 2.0)
        record3 = BLNRecord(1.0, 3.0)

        assert record1 == record2
        assert record1 != record3

    def test_bln_record_string_representation(self) -> None:
        """Test BLNRecord string representation."""
        record = BLNRecord(10.5, -20.3)
        str_repr = str(record)
        assert "10.5" in str_repr
        assert "-20.3" in str_repr


class TestParseBLN:
    """Test BLN file parsing functionality."""

    def test_parse_valid_bln(self, bln_file: Path) -> None:
        """Test parsing a valid BLN file."""
        records = parse_bln(bln_file)

        assert len(records) == 4
        assert records[0].x == 0.0
        assert records[0].y == 0.0
        assert records[3].x == 0.0
        assert records[3].y == 1.0

    def test_parse_complex_bln(self, tmp_path: Path, complex_bln_content: str) -> None:
        """Test parsing a complex BLN file with comments."""
        bln_file = tmp_path / "complex.bln"
        bln_file.write_text(complex_bln_content)

        records = parse_bln(bln_file)

        # Should parse 6 coordinate points (excluding header)
        assert len(records) == 6

    def test_parse_insufficient_points(self, invalid_bln_file: Path) -> None:
        """Test parsing BLN file with insufficient points."""
        with pytest.raises(GeometryError, match="at least 3 coordinate points"):
            parse_bln(invalid_bln_file)

    def test_parse_tab_separated(self, tmp_path: Path) -> None:
        """Test parsing tab-separated BLN file."""
        content = "0.0\t0.0\n1.0\t0.0\n1.0\t1.0\n0.0\t1.0\n"
        bln_file = tmp_path / "tabs.bln"
        bln_file.write_text(content)

        records = parse_bln(bln_file)
        assert len(records) == 4

    def test_parse_mixed_separators(self, tmp_path: Path) -> None:
        """Test parsing BLN file with mixed separators."""
        content = "0.0,0.0\n1.0\t0.0\n1.0,1.0\n0.0\t1.0\n"
        bln_file = tmp_path / "mixed.bln"
        bln_file.write_text(content)

        records = parse_bln(bln_file)
        assert len(records) == 4

    def test_parse_with_header_lines(self, tmp_path: Path) -> None:
        """Test parsing BLN file with header lines."""
        content = "# This is a header\n4 points\n0.0,0.0\n1.0,0.0\n1.0,1.0\n0.0,1.0\n"
        bln_file = tmp_path / "header.bln"
        bln_file.write_text(content)

        records = parse_bln(bln_file)
        assert len(records) == 4

    def test_parse_empty_lines(self, tmp_path: Path) -> None:
        """Test parsing BLN file with empty lines."""
        content = "0.0,0.0\n\n1.0,0.0\n\n1.0,1.0\n\n0.0,1.0\n"
        bln_file = tmp_path / "empty_lines.bln"
        bln_file.write_text(content)

        records = parse_bln(bln_file)
        assert len(records) == 4

    def test_parse_invalid_coordinate_lines(self, tmp_path: Path) -> None:
        """Test parsing BLN file with some invalid coordinate lines."""
        content = "0.0,0.0\ninvalid_line\n1.0,0.0\n1.0,1.0\n0.0,1.0\n"
        bln_file = tmp_path / "invalid_lines.bln"
        bln_file.write_text(content)

        records = parse_bln(bln_file)
        assert len(records) == 4  # Invalid line should be skipped

    def test_parse_large_coordinates(self, tmp_path: Path) -> None:
        """Test parsing BLN file with large coordinate values should skip OOB and error if <3 remain."""
        content = f"{1e6},{-1e6}\n{1e5},{-1e5}\n0,0\n"
        bln_file = tmp_path / "large.bln"
        bln_file.write_text(content)

        with pytest.raises(
            GeometryError,
            match="at least 3 coordinate points|Polygon requires at least 3",
        ):
            parse_bln(bln_file)

    def test_parse_precision_coordinates(self, tmp_path: Path) -> None:
        """Test parsing BLN file with high precision coordinates."""
        content = "0.123456789,0.987654321\n1.111111111,2.222222222\n3.333333333,4.444444444\n"
        bln_file = tmp_path / "precision.bln"
        bln_file.write_text(content)

        records = parse_bln(bln_file)
        assert len(records) == 3
        assert abs(records[0].x - 0.123456789) < 1e-9


class TestConvertFile:
    """Test file conversion functionality."""

    def test_convert_bln_to_geojson(self, bln_file: Path, tmp_path: Path) -> None:
        """Test converting BLN to GeoJSON."""
        output_file = tmp_path / "output.geojson"

        convert_file(bln_file, output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "FeatureCollection" in content

    def test_convert_creates_output_directory(
        self, bln_file: Path, tmp_path: Path
    ) -> None:
        """Test that conversion creates output directory if needed."""
        nested_output = tmp_path / "nested" / "dir" / "output.geojson"

        convert_file(bln_file, nested_output)

        assert nested_output.exists()
        assert nested_output.parent.exists()

    def test_convert_overwrites_existing_output(
        self, bln_file: Path, tmp_path: Path
    ) -> None:
        """Test that conversion overwrites existing output file."""
        output_file = tmp_path / "output.geojson"
        output_file.write_text("existing content")

        convert_file(bln_file, output_file)

        content = output_file.read_text()
        assert "existing content" not in content
        assert "FeatureCollection" in content

    @patch("baloon.formats.load_any")
    def test_convert_load_error(
        self, mock_load_any: Mock, bln_file: Path, tmp_path: Path
    ) -> None:
        """Test handling load errors during conversion."""
        mock_load_any.side_effect = Exception("Parse failed")
        output_file = tmp_path / "output.geojson"

        with pytest.raises(Exception, match="Parse failed"):
            convert_file(bln_file, output_file)

    @patch("baloon.formats.write_any")
    def test_convert_write_error(
        self, mock_write_any: Mock, bln_file: Path, tmp_path: Path
    ) -> None:
        """Test handling write errors during conversion."""
        mock_write_any.side_effect = Exception("Write failed")
        output_file = tmp_path / "output.geojson"

        with pytest.raises(Exception, match="Write failed"):
            convert_file(bln_file, output_file)

    def test_convert_various_formats(self, bln_file: Path, tmp_path: Path) -> None:
        """Test conversion between various supported formats."""
        # Test conversions to different formats using the BLN fixture
        formats_to_test = [
            ("test.geojson", "geojson"),
            ("test.gpkg", "gpkg"),
            ("test.kml", "kml"),
            ("test.svg", "svg"),
        ]

        for filename, format_name in formats_to_test:
            output_file = tmp_path / filename
            convert_file(bln_file, output_file)
            assert output_file.exists(), f"Failed to create {format_name} file"

    def test_convert_geojson_to_svg(self, geojson_file: Path, tmp_path: Path) -> None:
        """Test converting from GeoJSON (non-BLN) to SVG."""
        output_file = tmp_path / "out.svg"
        convert_file(geojson_file, output_file)
        assert output_file.exists()
        assert "<svg" in output_file.read_text()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_large_coordinates(self, tmp_path: Path) -> None:
        """Test parsing very large coordinate values should skip OOB and still succeed if enough points."""
        content = f"{1e10},{-1e10}\n{1e9},{-1e9}\n0,0\n1,1\n2,2\n"
        bln_file = tmp_path / "large.bln"
        bln_file.write_text(content)

        records = parse_bln(bln_file)
        # Out-of-bounds skipped; remaining 3 valid points form polygon
        assert len(records) == 3

    def test_minimal_valid_polygon(self, tmp_path: Path) -> None:
        """Test parsing minimal valid polygon (triangle)."""
        content = "0,0\n1,0\n0.5,1\n"
        bln_file = tmp_path / "triangle.bln"
        bln_file.write_text(content)

        records = parse_bln(bln_file)
        assert len(records) == 3

    def test_unicode_in_comments(self, tmp_path: Path) -> None:
        """Test handling of unicode characters in comment lines."""
        content = "# Região geográfica\n0,0\n1,0\n1,1\n0,1\n"
        bln_file = tmp_path / "unicode.bln"
        bln_file.write_text(content)

        records = parse_bln(bln_file)
        assert len(records) == 4

    def test_windows_line_endings(self, tmp_path: Path) -> None:
        """Test handling of Windows line endings (CRLF)."""
        content = "0,0\r\n1,0\r\n1,1\r\n0,1\r\n"
        bln_file = tmp_path / "windows.bln"
        bln_file.write_text(content, newline="")

        records = parse_bln(bln_file)
        assert len(records) == 4

    def test_very_long_coordinate_list(self, tmp_path: Path) -> None:
        """Test parsing very long coordinate list."""
        lines: list[str] = []
        for i in range(1000):
            x = i / 1000.0
            y = (i * i) / 1000000.0
            lines.append(f"{x},{y}")

        content = "\n".join(lines) + "\n"
        bln_file = tmp_path / "long.bln"
        bln_file.write_text(content)

        records = parse_bln(bln_file)
        assert len(records) == 1000
