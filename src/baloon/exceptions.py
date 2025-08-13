"""Custom exceptions for Baloon geospatial format processing.

This module defines semantic exceptions that provide clear, actionable error messages
for different types of failures that can occur during geospatial data processing.
"""


class BaloonError(Exception):
    """Base exception for all Baloon-related errors."""

    def __init__(self, message: str, path: str | None = None) -> None:
        self.path = path
        if path:
            super().__init__(f"{message} (file: {path})")
        else:
            super().__init__(message)


class FormatNotSupportedError(BaloonError):
    """Raised when a file format is not supported by any registered handler."""

    def __init__(self, extension: str, path: str | None = None) -> None:
        supported_formats = "BLN, Shapefile, GeoJSON, GeoPackage, KML, SVG"
        message = f"Format '.{extension}' is not supported. Supported formats: {supported_formats}"
        super().__init__(message, path)
        self.extension = extension


class FormatReadOnlyError(BaloonError):
    """Raised when attempting to write to a read-only format."""

    def __init__(self, format_name: str, path: str | None = None) -> None:
        message = f"Format '{format_name}' is read-only and cannot be used for output"
        super().__init__(message, path)
        self.format_name = format_name


class FormatWriteOnlyError(BaloonError):
    """Raised when attempting to read from a write-only format."""

    def __init__(self, format_name: str, path: str | None = None) -> None:
        message = f"Format '{format_name}' is write-only and cannot be used for input"
        super().__init__(message, path)
        self.format_name = format_name


class DependencyMissingError(BaloonError):
    """Raised when a required dependency is missing for a specific operation."""

    def __init__(
        self, package: str, operation: str, install_command: str | None = None
    ) -> None:
        message = f"Package '{package}' is required for {operation}"
        if install_command:
            message += f". Install with: {install_command}"
        super().__init__(message)
        self.package = package
        self.operation = operation
        self.install_command = install_command


class FileParsingError(BaloonError):
    """Raised when a file cannot be parsed due to format or content issues."""

    def __init__(self, message: str, path: str, line_number: int | None = None) -> None:
        if line_number:
            full_message = f"{message} (line {line_number})"
        else:
            full_message = message
        super().__init__(full_message, path)
        self.line_number = line_number


class GeometryError(BaloonError):
    """Raised when geometry processing fails."""

    def __init__(
        self, message: str, geometry_type: str | None = None, path: str | None = None
    ) -> None:
        if geometry_type:
            full_message = f"{message} (geometry type: {geometry_type})"
        else:
            full_message = message
        super().__init__(full_message, path)
        self.geometry_type = geometry_type


class InsufficientDataError(BaloonError):
    """Raised when input data is insufficient for the requested operation."""

    def __init__(
        self, message: str, required: int, found: int, path: str | None = None
    ) -> None:
        full_message = f"{message}. Required: {required}, found: {found}"
        super().__init__(full_message, path)
        self.required = required
        self.found = found


class CoordinateSystemError(BaloonError):
    """Raised when coordinate system operations fail."""

    def __init__(
        self,
        message: str,
        source_crs: str | None = None,
        target_crs: str | None = None,
        path: str | None = None,
    ) -> None:
        if source_crs and target_crs:
            full_message = f"{message} (from {source_crs} to {target_crs})"
        elif source_crs:
            full_message = f"{message} (CRS: {source_crs})"
        else:
            full_message = message
        super().__init__(full_message, path)
        self.source_crs = source_crs
        self.target_crs = target_crs
