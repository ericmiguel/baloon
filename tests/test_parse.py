from pathlib import Path

from baloon import parse_bln
from baloon.exceptions import GeometryError


def test_parse_basic(tmp_path: Path):
    content = """-43.1,-22.9\n-43.2,-22.9\n-43.2,-22.8\n-43.1,-22.8\n"""
    f = tmp_path / "square.bln"
    f.write_text(content)
    records = parse_bln(f)
    assert len(records) == 4
    assert records[0].x == -43.1


def test_parse_not_enough_points(tmp_path: Path):
    f = tmp_path / "bad.bln"
    f.write_text("10,10\n11,11\n")
    try:
        parse_bln(f)
    except GeometryError:
        pass
    else:  # pragma: no cover
        raise AssertionError("Expected GeometryError")


def test_parse_out_of_bounds(tmp_path: Path):
    content = """200,0\n0,0\n1,1\n2,2\n"""
    f = tmp_path / "oob.bln"
    f.write_text(content)

    records = parse_bln(f)
    # First line skipped; remaining 3 valid points are kept
    assert len(records) == 3
    assert records[0].x == 0
    assert records[-1].y == 2
