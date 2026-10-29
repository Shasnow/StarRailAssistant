"""Explicit UTF-8 contract for the CLI and its redirected frontend pipes."""
from __future__ import annotations

import sys


def configure_standard_streams() -> None:
    """Set codecs before cmd2/Rich or a logger retains a standard stream.

    Windows console streams already support Unicode, but redirected Python
    streams otherwise inherit the ANSI code page (e.g. CP1251). Reconfigure
    the existing wrappers rather than replacing handles or dropping characters.
    In-memory capture streams have no byte encoding and are left untouched.
    """
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if callable(reconfigure):
            reconfigure(encoding='utf-8', errors='strict')
