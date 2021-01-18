"""
Baloon command-line interface entry point.

Allows the package to be executed as a module with `python -m baloon`.
"""

from .cli import app


if __name__ == "__main__":
    app()
