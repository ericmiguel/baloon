"""Comprehensive tests for baloon.exceptions module.

Tests cover all custom exceptions, their initialization, and inheritance.
"""

from baloon.exceptions import BaloonError
from baloon.exceptions import CoordinateSystemError
from baloon.exceptions import DependencyMissingError
from baloon.exceptions import FileParsingError
from baloon.exceptions import FormatNotSupportedError
from baloon.exceptions import FormatReadOnlyError
from baloon.exceptions import FormatWriteOnlyError
from baloon.exceptions import GeometryError
from baloon.exceptions import InsufficientDataError


class TestBaloonError:
    """Test base BaloonError exception."""

    def test_basic_message(self):
        """Test basic error message."""
        error = BaloonError("Test error message")
        assert str(error) == "Test error message"
        assert error.path is None

    def test_message_with_path(self):
        """Test error message with file path."""
        error = BaloonError("Test error", "/path/to/file.bln")
        assert str(error) == "Test error (file: /path/to/file.bln)"
        assert error.path == "/path/to/file.bln"

    def test_inheritance(self):
        """Test that BaloonError inherits from Exception."""
        error = BaloonError("Test")
        assert isinstance(error, Exception)
        assert isinstance(error, BaloonError)


class TestFormatNotSupportedError:
    """Test FormatNotSupportedError exception."""

    def test_basic_usage(self):
        """Test basic format not supported error."""
        error = FormatNotSupportedError("xyz")
        expected_msg = (
            "Format '.xyz' is not supported. "
            "Supported formats: BLN, Shapefile, GeoJSON, GeoPackage, KML, SVG"
        )
        assert str(error) == expected_msg
        assert error.extension == "xyz"
        assert error.path is None

    def test_with_path(self):
        """Test format error with file path."""
        error = FormatNotSupportedError("abc", "/path/to/file.abc")
        assert "/path/to/file.abc" in str(error)
        assert error.extension == "abc"
        assert error.path == "/path/to/file.abc"

    def test_inheritance(self):
        """Test inheritance from BaloonError."""
        error = FormatNotSupportedError("xyz")
        assert isinstance(error, BaloonError)
        assert isinstance(error, FormatNotSupportedError)


class TestFormatReadOnlyError:
    """Test FormatReadOnlyError exception."""

    def test_basic_usage(self):
        """Test basic read-only format error."""
        error = FormatReadOnlyError("SVG")
        expected_msg = "Format 'SVG' is read-only and cannot be used for output"
        assert str(error) == expected_msg
        assert error.format_name == "SVG"

    def test_with_path(self):
        """Test read-only error with path."""
        error = FormatReadOnlyError("SVG", "/path/to/file.svg")
        assert "SVG" in str(error)
        assert "/path/to/file.svg" in str(error)
        assert error.format_name == "SVG"
        assert error.path == "/path/to/file.svg"

    def test_inheritance(self):
        """Test inheritance from BaloonError."""
        error = FormatReadOnlyError("SVG")
        assert isinstance(error, BaloonError)


class TestFormatWriteOnlyError:
    """Test FormatWriteOnlyError exception."""

    def test_basic_usage(self):
        """Test basic write-only format error."""
        error = FormatWriteOnlyError("SPECIAL")
        expected_msg = "Format 'SPECIAL' is write-only and cannot be used for input"
        assert str(error) == expected_msg
        assert error.format_name == "SPECIAL"

    def test_with_path(self):
        """Test write-only error with path."""
        error = FormatWriteOnlyError("SPECIAL", "/path/to/file.special")
        assert "SPECIAL" in str(error)
        assert "/path/to/file.special" in str(error)
        assert error.format_name == "SPECIAL"

    def test_inheritance(self):
        """Test inheritance from BaloonError."""
        error = FormatWriteOnlyError("SPECIAL")
        assert isinstance(error, BaloonError)


class TestDependencyMissingError:
    """Test DependencyMissingError exception."""

    def test_basic_usage(self):
        """Test basic dependency missing error."""
        error = DependencyMissingError("numpy", "array processing")
        expected_msg = "Package 'numpy' is required for array processing"
        assert str(error) == expected_msg
        assert error.package == "numpy"
        assert error.operation == "array processing"
        assert error.install_command is None

    def test_with_install_command(self):
        """Test dependency error with install command."""
        error = DependencyMissingError("numpy", "array processing", "pip install numpy")
        expected_msg = "Package 'numpy' is required for array processing. Install with: pip install numpy"
        assert str(error) == expected_msg
        assert error.install_command == "pip install numpy"

    def test_inheritance(self):
        """Test inheritance from BaloonError."""
        error = DependencyMissingError("package", "operation")
        assert isinstance(error, BaloonError)


class TestFileParsingError:
    """Test FileParsingError exception."""

    def test_basic_usage(self):
        """Test basic file parsing error."""
        error = FileParsingError("Invalid format", "/path/to/file.bln")
        assert str(error) == "Invalid format (file: /path/to/file.bln)"
        assert error.path == "/path/to/file.bln"
        assert error.line_number is None

    def test_with_line_number(self):
        """Test parsing error with line number."""
        error = FileParsingError("Invalid coordinate", "/path/to/file.bln", 42)
        expected_msg = "Invalid coordinate (line 42) (file: /path/to/file.bln)"
        assert str(error) == expected_msg
        assert error.line_number == 42

    def test_inheritance(self):
        """Test inheritance from BaloonError."""
        error = FileParsingError("Error", "/path")
        assert isinstance(error, BaloonError)


class TestGeometryError:
    """Test GeometryError exception."""

    def test_basic_usage(self):
        """Test basic geometry error."""
        error = GeometryError("Invalid geometry")
        assert str(error) == "Invalid geometry"
        assert error.geometry_type is None
        assert error.path is None

    def test_with_geometry_type(self):
        """Test geometry error with type specification."""
        error = GeometryError("Invalid coordinates", "Polygon")
        expected_msg = "Invalid coordinates (geometry type: Polygon)"
        assert str(error) == expected_msg
        assert error.geometry_type == "Polygon"

    def test_with_path(self):
        """Test geometry error with file path."""
        error = GeometryError("Invalid geometry", "Point", "/path/to/file.bln")
        assert "Invalid geometry" in str(error)
        assert "Point" in str(error)
        assert "/path/to/file.bln" in str(error)
        assert error.path == "/path/to/file.bln"

    def test_inheritance(self):
        """Test inheritance from BaloonError."""
        error = GeometryError("Error")
        assert isinstance(error, BaloonError)


class TestInsufficientDataError:
    """Test InsufficientDataError exception."""

    def test_basic_usage(self):
        """Test basic insufficient data error."""
        error = InsufficientDataError("Not enough points", 3, 2)
        expected_msg = "Not enough points. Required: 3, found: 2"
        assert str(error) == expected_msg
        assert error.required == 3
        assert error.found == 2
        assert error.path is None

    def test_with_path(self):
        """Test insufficient data error with path."""
        error = InsufficientDataError("Not enough points", 4, 1, "/path/to/file.bln")
        assert "Not enough points" in str(error)
        assert "Required: 4" in str(error)
        assert "found: 1" in str(error)
        assert "/path/to/file.bln" in str(error)
        assert error.path == "/path/to/file.bln"

    def test_inheritance(self):
        """Test inheritance from BaloonError."""
        error = InsufficientDataError("Error", 1, 0)
        assert isinstance(error, BaloonError)


class TestCoordinateSystemError:
    """Test CoordinateSystemError exception."""

    def test_basic_usage(self):
        """Test basic coordinate system error."""
        error = CoordinateSystemError("CRS transformation failed")
        assert str(error) == "CRS transformation failed"
        assert error.source_crs is None
        assert error.target_crs is None
        assert error.path is None

    def test_with_source_crs(self):
        """Test CRS error with source CRS."""
        error = CoordinateSystemError("Invalid CRS", "EPSG:4326")
        expected_msg = "Invalid CRS (CRS: EPSG:4326)"
        assert str(error) == expected_msg
        assert error.source_crs == "EPSG:4326"

    def test_with_both_crs(self):
        """Test CRS error with source and target CRS."""
        error = CoordinateSystemError("Transform failed", "EPSG:4326", "EPSG:3857")
        expected_msg = "Transform failed (from EPSG:4326 to EPSG:3857)"
        assert str(error) == expected_msg
        assert error.source_crs == "EPSG:4326"
        assert error.target_crs == "EPSG:3857"

    def test_with_path(self):
        """Test CRS error with file path."""
        error = CoordinateSystemError(
            "CRS issue", "EPSG:4326", "EPSG:3857", "/path/to/file.shp"
        )
        assert "CRS issue" in str(error)
        assert "EPSG:4326" in str(error)
        assert "EPSG:3857" in str(error)
        assert "/path/to/file.shp" in str(error)
        assert error.path == "/path/to/file.shp"

    def test_inheritance(self):
        """Test inheritance from BaloonError."""
        error = CoordinateSystemError("Error")
        assert isinstance(error, BaloonError)


class TestExceptionHierarchy:
    """Test exception hierarchy and relationships."""

    def test_all_exceptions_inherit_from_baloon_error(self, all_exceptions):
        """Test that all custom exceptions inherit from BaloonError."""
        for exception_class in all_exceptions:
            if exception_class != BaloonError:
                # Create instance with minimal required args
                if exception_class == FormatNotSupportedError:
                    instance = exception_class("test")
                elif exception_class == FormatReadOnlyError:
                    instance = exception_class("test")
                elif exception_class == FormatWriteOnlyError:
                    instance = exception_class("test")
                elif exception_class == DependencyMissingError:
                    instance = exception_class("package", "operation")
                elif exception_class == FileParsingError:
                    instance = exception_class("message", "path")
                elif exception_class == GeometryError:
                    instance = exception_class("message")
                elif exception_class == InsufficientDataError:
                    instance = exception_class("message", 1, 0)
                elif exception_class == CoordinateSystemError:
                    instance = exception_class("message")
                else:
                    instance = exception_class("message")

                assert isinstance(instance, BaloonError)
                assert isinstance(instance, Exception)

    def test_exception_catching(self):
        """Test that specific exceptions can be caught as BaloonError."""
        try:
            raise FormatNotSupportedError("test")
        except BaloonError as e:
            assert isinstance(e, FormatNotSupportedError)
            assert isinstance(e, BaloonError)

        try:
            raise GeometryError("test error")
        except BaloonError as e:
            assert isinstance(e, GeometryError)
            assert isinstance(e, BaloonError)

    def test_exception_attributes_preserved(self):
        """Test that exception-specific attributes are preserved."""
        # Test FormatNotSupportedError
        format_error = FormatNotSupportedError("xyz", "/path")
        try:
            raise format_error
        except BaloonError as e:
            assert hasattr(e, "extension")
            assert e.extension == "xyz"

        # Test InsufficientDataError
        data_error = InsufficientDataError("message", 5, 2, "/path")
        try:
            raise data_error
        except BaloonError as e:
            assert hasattr(e, "required")
            assert hasattr(e, "found")
            assert e.required == 5
            assert e.found == 2
