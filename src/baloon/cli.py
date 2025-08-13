"""Command-line interface for Baloon geospatial format converter.

This module provides a Typer-based CLI for converting between various
geospatial file formats including BLN, Shapefile, GeoJSON, KML,
GeoPackage, and SVG.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from rich.console import Console
from rich.progress import track
import typer

from baloon.core import convert_file
from baloon.exceptions import BaloonError


app = typer.Typer(
    name="baloon",
    help="Convert a geospatial file from one format to another",
    no_args_is_help=True,
)
console = Console()


@app.callback(invoke_without_command=True)
def main(
    input_path: Annotated[
        Path,
        typer.Argument(help="Input file path", show_default=False),
    ],
    output_path: Annotated[
        Path,
        typer.Argument(help="Output file path", show_default=False),
    ],
    input_format: Annotated[
        str | None,
        typer.Option(
            "--input-format",
            "-i",
            help="Input format (auto-detected if not specified)",
        ),
    ] = None,
    output_format: Annotated[
        str | None,
        typer.Option(
            "--output-format",
            "-o",
            help="Output format (detected from extension if not specified)",
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite output file if it exists"),
    ] = False,
) -> None:
    """Convert a geospatial file from one format to another.

    Supports BLN (read-only), Shapefile, GeoJSON, KML, GeoPackage (GPKG), and SVG (write-only).
    """
    try:
        # Directory batch conversion path
        if input_path.is_dir():
            if output_format is None:
                console.print(
                    "❌ When input is a directory, please specify --output-format (e.g., geojson).",
                    style="red",
                )
                raise typer.Exit(2)

            target_dir = output_path
            if target_dir.exists() and not target_dir.is_dir():
                console.print(
                    f"❌ Output path '{target_dir}' must be a directory when converting a folder.",
                    style="red",
                )
                raise typer.Exit(2)
            target_dir.mkdir(parents=True, exist_ok=True)

            # Pre-scan files to warn and build conversion list
            from baloon.exceptions import (
                FormatNotSupportedError as FormatNotSupportedError,
            )
            from baloon.formats import detect_format as _detect_format

            files_to_convert: list[tuple[Path, Path]] = []
            unsupported_count = 0
            write_only_count = 0

            for file in input_path.glob("**/*"):
                if not file.is_file():
                    continue
                try:
                    handler = _detect_format(file)
                except FormatNotSupportedError:
                    unsupported_count += 1
                    console.print(
                        f"⚠️ Skipping unsupported file: {file}", style="yellow"
                    )
                    continue
                if not handler.reader:
                    write_only_count += 1
                    console.print(
                        f"⚠️ Skipping write-only format '{handler.name}': {file}",
                        style="yellow",
                    )
                    continue
                rel_path = file.relative_to(input_path)
                out_file = target_dir / rel_path.with_suffix(f".{output_format}")
                out_file.parent.mkdir(parents=True, exist_ok=True)
                files_to_convert.append((file, out_file))

            if not files_to_convert:
                console.print("No convertible files found.", style="yellow")
                # Still exit success (nothing to do)
                return

            console.print(
                f"Converting directory '{input_path}' to '{output_format}' into '{target_dir}'..."
            )

            for src, dst in track(files_to_convert, description="Converting..."):
                convert_file(src, dst)

            console.print(
                f"✓ Successfully converted {len(files_to_convert)} file(s) to '{target_dir}'",
                style="green",
            )
            return

        # Single-file conversion path
        # Check if output file exists and overwrite is not set
        if output_path.exists() and not overwrite:
            console.print(
                f"❌ Output file '{output_path}' already exists. Use --overwrite to replace it.",
                style="red",
            )
            raise typer.Exit(2)

        # Detect formats if not specified
        if input_format is None:
            try:
                from baloon.formats import detect_format as _detect_format

                handler = _detect_format(input_path)
                input_format = handler.name
                console.print(f"Detected input format: {input_format}")
            except Exception as e:
                from baloon.exceptions import (
                    FormatNotSupportedError as FormatNotSupportedError,
                )

                if isinstance(e, FormatNotSupportedError):
                    console.print(f"❌ Unsupported input format: {e}", style="red")
                    raise typer.Exit(2) from e
                raise

        if output_format is None:
            try:
                from baloon.formats import detect_format as _detect_format

                handler = _detect_format(output_path)
                output_format = handler.name
                console.print(f"Detected output format: {output_format}")
            except Exception as e:
                from baloon.exceptions import (
                    FormatNotSupportedError as FormatNotSupportedError,
                )

                if isinstance(e, FormatNotSupportedError):
                    console.print(f"❌ Unsupported output format: {e}", style="red")
                    raise typer.Exit(2) from e
                raise

        # Perform conversion with progress tracking
        console.print(
            f"Converting '{input_path}' ({input_format}) to '{output_path}' ({output_format})..."
        )

        for _ in track([1], description="Converting..."):
            convert_file(input_path, output_path)

        console.print(f"✓ Successfully converted to '{output_path}'", style="green")

    except BaloonError as e:
        console.print(f"❌ Conversion error: {e}", style="red")
        raise typer.Exit(1) from e
    except typer.Exit:
        # Let Typer handle controlled exits without double-reporting
        raise
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}", style="red")
        raise typer.Exit(2) from e


if __name__ == "__main__":
    app()
