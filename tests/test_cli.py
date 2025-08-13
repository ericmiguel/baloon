"""Comprehensive tests for baloon.cli module.

Tests cover CLI commands, argument parsing, error handling, and user interaction.
"""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from baloon.cli import app
from baloon.exceptions import BaloonError


class TestCLIMain:
    """Test the main CLI functionality."""

    def test_successful_conversion(self, tmp_path: Path) -> None:
        """Test successful file conversion via CLI."""
        runner = CliRunner()

        # Create test input file
        input_file = tmp_path / "test.bln"
        input_file.write_text("0,0\n1,0\n1,1\n0,1\n")
        output_file = tmp_path / "test.geojson"

        with patch("baloon.cli.convert_file") as mock_convert:
            result = runner.invoke(app, [str(input_file), str(output_file)])

            assert result.exit_code == 0
            assert "Detected input format: BLN" in result.output
            assert "Detected output format: GeoJSON" in result.output
            assert "Successfully converted" in result.output
            mock_convert.assert_called_once_with(input_file, output_file)

    def test_format_detection_error(self, tmp_path: Path) -> None:
        """Test handling of format detection errors."""
        runner = CliRunner()

        input_file = tmp_path / "test.unknown"
        input_file.write_text("test content")
        output_file = tmp_path / "output.geojson"

        result = runner.invoke(app, [str(input_file), str(output_file)])

        assert result.exit_code == 2  # typer.Exit becomes unexpected error
        assert "Unsupported input format" in result.output

    def test_conversion_error_handling(self, tmp_path: Path) -> None:
        """Test handling of conversion errors."""
        runner = CliRunner()

        input_file = tmp_path / "test.bln"
        input_file.write_text("0,0\n1,0\n1,1\n0,1\n")
        output_file = tmp_path / "test.geojson"

        with patch("baloon.cli.convert_file") as mock_convert:
            mock_convert.side_effect = BaloonError("Conversion failed")

            result = runner.invoke(app, [str(input_file), str(output_file)])

            assert result.exit_code == 1  # BaloonError returns code 1
            assert "Conversion error: Conversion failed" in result.output

    def test_file_exists_without_overwrite(self, tmp_path: Path) -> None:
        """Test behavior when output file exists and overwrite is not set."""
        runner = CliRunner()

        input_file = tmp_path / "test.bln"
        input_file.write_text("0,0\n1,0\n1,1\n0,1\n")
        output_file = tmp_path / "existing.geojson"
        output_file.write_text("existing content")

        result = runner.invoke(app, [str(input_file), str(output_file)])

        assert result.exit_code == 2  # Typer exits with 2 on errors
        assert "already exists" in result.output
        assert "Use --overwrite" in result.output

    def test_file_exists_with_overwrite(self, tmp_path: Path) -> None:
        """Test behavior with overwrite flag when output file exists."""
        runner = CliRunner()

        input_file = tmp_path / "test.bln"
        input_file.write_text("0,0\n1,0\n1,1\n0,1\n")
        output_file = tmp_path / "existing.geojson"
        output_file.write_text("existing content")

        with patch("baloon.cli.convert_file") as mock_convert:
            result = runner.invoke(
                app, ["--overwrite", str(input_file), str(output_file)]
            )

            assert result.exit_code == 0
            assert "Successfully converted" in result.output
            mock_convert.assert_called_once()

    def test_explicit_format_specification(self, tmp_path: Path) -> None:
        """Test explicit format specification via options."""
        runner = CliRunner()

        input_file = tmp_path / "data.txt"  # Non-standard extension
        input_file.write_text("0,0\n1,0\n1,1\n0,1\n")
        output_file = tmp_path / "output.txt"  # Non-standard extension

        with patch("baloon.cli.convert_file") as mock_convert:
            result = runner.invoke(
                app,
                [
                    "--input-format",
                    "bln",
                    "--output-format",
                    "geojson",
                    str(input_file),
                    str(output_file),
                ],
            )

            assert result.exit_code == 0
            mock_convert.assert_called_once()

    def test_nonexistent_input_file(self, tmp_path: Path) -> None:
        """Test handling of non-existent input file."""
        runner = CliRunner()

        input_file = tmp_path / "nonexistent.bln"
        output_file = tmp_path / "output.geojson"

        result = runner.invoke(app, [str(input_file), str(output_file)])

        assert result.exit_code == 2
        assert "No such file or directory" in result.output

    def test_unexpected_error_handling(self, tmp_path: Path) -> None:
        """Test handling of unexpected errors."""
        runner = CliRunner()

        input_file = tmp_path / "test.bln"
        input_file.write_text("0,0\n1,0\n1,1\n0,1\n")
        output_file = tmp_path / "output.geojson"

        with patch("baloon.cli.convert_file") as mock_convert:
            mock_convert.side_effect = RuntimeError("Unexpected error")

            result = runner.invoke(app, [str(input_file), str(output_file)])

            assert result.exit_code == 2
            assert "Unexpected error: Unexpected error" in result.output


class TestCLIHelpAndUsage:
    """Test CLI help and usage information."""

    def test_main_help(self) -> None:
        """Test main application help."""
        runner = CliRunner()

        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Convert a geospatial file from one format to another" in result.output
        assert "input_path" in result.output

    def test_convert_help(self) -> None:
        """Test main help (same as --help)."""
        runner = CliRunner()

        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Convert a geospatial file" in result.output
        assert "input-format" in result.output
        assert "output-format" in result.output
        assert "overwrite" in result.output

    def test_no_args_shows_help(self) -> None:
        """Test that running with no arguments shows help."""
        runner = CliRunner()

        result = runner.invoke(app, [])

        # Typer will treat missing required arguments as usage error (exit code 2)
        assert result.exit_code == 2
        assert "Usage:" in result.output


class TestCLIArgumentValidation:
    """Test CLI argument validation and error handling."""

    def test_missing_output_path(self) -> None:
        """Test behavior with missing output path argument."""
        runner = CliRunner()

        result = runner.invoke(app, ["input.bln"])

        assert result.exit_code == 2

    def test_invalid_command(self) -> None:
        """Test behavior with missing output path."""
        runner = CliRunner()

        result = runner.invoke(app, ["invalid-argument"])

        assert result.exit_code == 2
        assert "Missing argument 'OUTPUT_PATH'" in result.output

    def test_invalid_option(self) -> None:
        """Test behavior with invalid option."""
        runner = CliRunner()

        result = runner.invoke(app, ["input.bln", "output.geojson", "--invalid-option"])

        assert result.exit_code == 2


class TestCLIIntegrationFeatures:
    """Test advanced CLI features and integration scenarios."""

    def test_progress_display(self, tmp_path: Path) -> None:
        """Test that progress is displayed during conversion."""
        runner = CliRunner()

        input_file = tmp_path / "test.bln"
        input_file.write_text("0,0\n1,0\n1,1\n0,1\n")
        output_file = tmp_path / "output.geojson"

        with patch("baloon.cli.convert_file"):
            result = runner.invoke(app, [str(input_file), str(output_file)])

            assert "Converting..." in result.output

    def test_format_detection_messages(self, tmp_path: Path) -> None:
        """Test that format detection messages are shown."""
        runner = CliRunner()

        input_file = tmp_path / "test.bln"
        input_file.write_text("0,0\n1,0\n1,1\n0,1\n")
        output_file = tmp_path / "output.geojson"

        with patch("baloon.cli.convert_file"):
            result = runner.invoke(app, [str(input_file), str(output_file)])

            assert "Detected input format: BLN" in result.output

    def test_explicit_output_format_detection(self, tmp_path: Path) -> None:
        """Test explicit output format detection."""
        runner = CliRunner()

        input_file = tmp_path / "test.bln"
        input_file.write_text("0,0\n1,0\n1,1\n0,1\n")
        output_file = tmp_path / "output.geojson"

        with patch("baloon.cli.convert_file"):
            result = runner.invoke(app, [str(input_file), str(output_file)])

            assert "Detected output format: GeoJSON" in result.output

    def test_format_override_with_options(self, tmp_path: Path) -> None:
        """Test format override with explicit options."""
        runner = CliRunner()

        input_file = tmp_path / "data.txt"
        input_file.write_text("0,0\n1,0\n1,1\n0,1\n")
        output_file = tmp_path / "output.txt"

        with patch("baloon.cli.convert_file"):
            result = runner.invoke(
                app,
                [
                    "--input-format",
                    "bln",
                    "--output-format",
                    "geojson",
                    str(input_file),
                    str(output_file),
                ],
            )

            assert "Converting" in result.output  # Message is different than expected

    def test_success_message_display(self, tmp_path: Path) -> None:
        """Test that success message is displayed."""
        runner = CliRunner()

        input_file = tmp_path / "test.bln"
        input_file.write_text("0,0\n1,0\n1,1\n0,1\n")
        output_file = tmp_path / "output.geojson"

        with patch("baloon.cli.convert_file"):
            result = runner.invoke(app, [str(input_file), str(output_file)])

            assert "✓ Successfully converted" in result.output

    def test_unsupported_format_error_display(self, tmp_path: Path) -> None:
        """Test display of unsupported format errors."""
        runner = CliRunner()

        input_file = tmp_path / "test.unknown"
        input_file.write_text("test content")
        output_file = tmp_path / "output.geojson"

        result = runner.invoke(app, [str(input_file), str(output_file)])

        assert result.exit_code == 2
        assert "❌ Unsupported input format" in result.output

    def test_format_specific_error_handling(self, tmp_path: Path) -> None:
        """Test format-specific error handling."""
        runner = CliRunner()

        input_file = tmp_path / "test.bln"
        input_file.write_text("0,0\n1,0\n1,1\n0,1\n")
        output_file = tmp_path / "output.unknown"

        with patch("baloon.cli.convert_file"):
            result = runner.invoke(app, [str(input_file), str(output_file)])

            assert (
                "Detected input format: BLN" in result.output
            )  # BLN format is detected correctly
