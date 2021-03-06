"""URL related utilities.
"""

__version__ = '[library version:1.0.1]'[17:-1]

# Parse the version info
try:
    version_info = map(int, __version__.split('.'))
except ValueError:
    version_info = (None, None, None)
else:
    if len(version_info) != 3:
        version_info = (None, None, None)
    else:
        version_info = tuple(version_info)
