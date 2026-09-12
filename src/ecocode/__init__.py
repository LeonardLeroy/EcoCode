"""EcoCode package."""

from importlib.metadata import PackageNotFoundError, version as _version

__all__ = ["__version__"]

try:
    __version__ = _version("ecocode-cli")
except PackageNotFoundError:  # running from a source checkout without an install
    __version__ = "0.0.0+dev"
