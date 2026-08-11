"""just-module-creator — an MCP server for authoring just-dna annotation modules."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("just-module-creator")
except PackageNotFoundError:  # running from a source checkout without install
    __version__ = "0.0.0+local"
