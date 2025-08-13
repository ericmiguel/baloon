"""Command-line interface for Baloon.

Provides a modern Typer-based CLI with Rich output formatting for converting
geospatial polygon files between formats like BLN, Shapefile, GeoJSON, and SVG.

The CLI supports single file conversion, batch directory processing, file inspection,
and format discovery with beautifully formatted output tables.
"""

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from . import __version__
from .core import BLNParseError, convert_path, parse_bln
from .formats import list_formats, load_any, write_any

console = Console()
app = typer.Typer(help="Baloon - Convert BLN polygon files to modern geospatial formats.")


def _configure_logging(verbosity: int) -> None:
    """Configure Rich logging based on verbosity level.

    Parameters
    ----------
    verbosity : int
        Verbosity level: 0=WARNING, 1=INFO, 2+=DEBUG
    """
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, show_time=False, show_path=False)],
    )


@app.callback()
def _main(
    ctx: typer.Context,
    verbose: Annotated[
        int, typer.Option("-v", "--verbose", count=True, help="Increase verbosity (-v, -vv).")
    ] = 0,
    version: Annotated[bool, typer.Option("--version", help="Show version and exit.")] = False,
) -> None:
    """Main callback for global options."""
    if version:
        console.print(f"baloon version [bold]{__version__}[/bold]")
        raise typer.Exit()
    _configure_logging(verbose)
    ctx.ensure_object(dict)


@app.command("convert")
def convert_cmd(
    input_path: Annotated[Path, typer.Argument(help="Input file (BLN / SHP / GeoJSON)")],
    to: Annotated[list[str] | None, typer.Option("-t", "--to", help="Target format(s)")] = None,
    out_dir: Annotated[Path | None, typer.Option("-o", "--out", help="Output directory")] = None,
) -> None:
    """Convert a single file to one or more target formats.

    Supports conversion between BLN, Shapefile, GeoJSON, and SVG formats.
    Auto-detects input format from file extension and creates output files
    with the specified target extensions.

    Examples:
        baloon convert boundary.bln --to geojson svg
        baloon convert data.geojson --to shp --out ./output/
    """
    if to is None:
        to = ["geojson"]

    if not input_path.exists():
        console.print(f"[red]Error[/red]: Input file not found: {input_path}")
        raise typer.Exit(1)

    # Load input file using format registry
    try:
        gdf = load_any(input_path)
    except Exception as e:
        console.print(f"[red]Error[/red]: Failed to load {input_path.name}: {e}")
        raise typer.Exit(1) from e

    # Set up output directory
    out_directory = out_dir or input_path.parent
    out_directory.mkdir(parents=True, exist_ok=True)

    # Convert to each target format
    table = Table(title=f"Converting {input_path.name}")
    table.add_column("Output", style="cyan")
    table.add_column("Status", style="green")

    for fmt in to:
        ext = fmt.lower()
        out_path = out_directory / f"{input_path.stem}.{ext}"
        try:
            write_any(gdf, out_path, ext)
            table.add_row(str(out_path), "✓ Success")
        except Exception as e:
            table.add_row(str(out_path), f"✗ Error: {e}")

    console.print(table)


@app.command("batch")
def batch_cmd(
    folder: Annotated[Path, typer.Argument(help="Folder containing BLN files")],
    to: Annotated[str, typer.Option("-t", "--to", help="Target format")] = "geojson",
    out_dir: Annotated[Path | None, typer.Option("-o", "--out", help="Output directory")] = None,
) -> None:
    """Convert all BLN files in a directory to the target format.

    Recursively processes all .bln files in the specified directory,
    preserving the directory structure in the output.

    Examples:
        baloon batch ./data/ --to geojson
        baloon batch ./boundaries/ --to svg --out ./svg_output/
    """
    if not folder.exists() or not folder.is_dir():
        console.print(f"[red]Error[/red]: Directory not found: {folder}")
        raise typer.Exit(1)

    # Find all BLN files
    bln_files = list(folder.glob("**/*.bln"))
    if not bln_files:
        console.print(f"[yellow]Warning[/yellow]: No BLN files found in {folder}")
        return

    table = Table(title=f"Batch Converting {len(bln_files)} BLN files")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="green")

    success_count = 0
    for bln_file in bln_files:
        try:
            convert_path(bln_file, to, out_dir)
            table.add_row(bln_file.name, "✓ Converted")
            success_count += 1
        except Exception as e:
            table.add_row(bln_file.name, f"✗ {e}")

    console.print(table)
    console.print(f"\n[green]Converted {success_count}/{len(bln_files)} files successfully[/green]")


@app.command("formats")
def formats_cmd() -> None:
    """List all supported file formats.

    Shows which formats can be read from and written to, along with
    descriptions of each format's capabilities.
    """
    table = Table(title="Supported File Formats")
    table.add_column("Format", style="bold")
    table.add_column("Extensions", style="cyan")
    table.add_column("Read", justify="center")
    table.add_column("Write", justify="center")
    table.add_column("Description")

    for handler in list_formats():
        exts = ", ".join(f".{ext}" for ext in handler.extensions)
        read_mark = "✓" if handler.reader else "✗"
        write_mark = "✓" if handler.writer else "✗"

        table.add_row(
            handler.name, exts, read_mark, write_mark, handler.description or "No description"
        )
    console.print(table)


@app.command("inspect")
def inspect_cmd(file: Annotated[Path, typer.Argument(help="BLN file to inspect")]) -> None:
    """Inspect a BLN file and show coordinate information.

    Parses the BLN file and displays statistics about the coordinate
    data, including point count and bounding box information.

    Examples:
        baloon inspect boundary.bln
    """
    if not file.exists():
        console.print(f"[red]Error[/red]: File not found: {file}")
        raise typer.Exit(1)

    try:
        records = parse_bln(file)
    except BLNParseError as e:
        console.print(f"[red]Parse error[/red]: {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error[/red]: {e}")
        raise typer.Exit(1) from e

    # Calculate basic statistics
    xs = [r.x for r in records]
    ys = [r.y for r in records]

    table = Table(title=f"BLN File Analysis: {file.name}")
    table.add_column("Property", style="bold")
    table.add_column("Value", style="cyan")

    table.add_row("Point Count", str(len(records)))
    table.add_row("Min X", f"{min(xs):.6f}")
    table.add_row("Max X", f"{max(xs):.6f}")
    table.add_row("Min Y", f"{min(ys):.6f}")
    table.add_row("Max Y", f"{max(ys):.6f}")
    table.add_row("Width", f"{max(xs) - min(xs):.6f}")
    table.add_row("Height", f"{max(ys) - min(ys):.6f}")

    console.print(table)

    # Show first few points
    if records:
        console.print("\n[bold]First 5 coordinates:[/bold]")
        coord_table = Table()
        coord_table.add_column("Index", justify="right")
        coord_table.add_column("X", justify="right")
        coord_table.add_column("Y", justify="right")

        for i, record in enumerate(records[:5]):
            coord_table.add_row(str(i), f"{record.x:.6f}", f"{record.y:.6f}")

        console.print(coord_table)


if __name__ == "__main__":
    app()
