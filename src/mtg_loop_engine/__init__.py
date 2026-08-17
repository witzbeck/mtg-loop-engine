"""MTG Loop Engine: witness verification for repeatable two-card loops."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mtg-loop-engine")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.1.0"

__all__ = ["__version__"]
