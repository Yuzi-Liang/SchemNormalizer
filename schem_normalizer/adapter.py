from __future__ import annotations

from pathlib import Path

from .adapter_nbtlib import read_schematic as read_schematic_nbtlib
from .adapter_nbtlib import write_schematic as write_schematic_nbtlib


def read_schematic(path: Path):
    return read_schematic_nbtlib(path)


def write_schematic(schematic, path: Path):
    return write_schematic_nbtlib(schematic, path)
