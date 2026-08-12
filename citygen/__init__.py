"""citygen - Chronopolis repository analyzer.

Turns a git repository into a `city.json` document that the Chronopolis
viewer renders as a navigable 3D city.

Public entry point: `python -m citygen build <repo> -o city.json`
"""

__version__ = "0.1.0"
SCHEMA = "chronopolis.city/1"
